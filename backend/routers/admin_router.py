import json
import asyncio
import httpx
import logging
from urllib.parse import quote_plus
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from database import get_db, SessionLocal
from models import User, UserSettings, Template, TokenUsage, GenerationJob
from schemas import (
    AdminUserResponse,
    AdminUserCreateRequest,
    AdminUserRoleUpdateRequest,
    TemplateResponse,
    TemplateListItem,
    TemplateGenerateRequest,
    TemplateUpdateRequest,
    PresentationContent,
    SlideData,
    GenerationJobResponse,
)
from pydantic import BaseModel
from typing import Optional

class AssetResponse(BaseModel):
    id: int
    url: str
    label: str
    asset_type: str
    
    class Config:
        from_attributes = True

class AssetCreateRequest(BaseModel):
    url: str
    label: str = ""
    asset_type: str = "image"

from auth import get_current_user, hash_password
from config import SECRET_KEY, ALGORITHM
from services.llm_service import generate_template_content
from services.auto_design_service import apply_auto_design
from services.asset_match_service import find_best_asset_url
from services.image_service import fetch_images_with_fallback, fetch_image_with_fallback
from services.stream_manager import stream_manager
from services.feedback_service import get_feedback_rules_as_prompt
from routers.ppt_router import (
    _authenticate_from_token,
    _global_media_fetch_semaphore,
    _provisional_title_from_prompt,
    _run_with_heartbeat,
    _stream_loading_slides,
    _loading_slide,
    SLIDE_BUILD_CONCURRENCY,
    as_dict, as_list, normalize_stats, extract_visual,
    search_iconify_icon, build_slide_data,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _update_job(db: Session, job_id: int, **fields):
    from datetime import datetime, timezone
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if not job:
        return None
    for key, value in fields.items():
        if hasattr(job, key):
            setattr(job, key, value)
    job.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job




def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# ─── Users ─────────────────────────────────────────
@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [AdminUserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=AdminUserResponse)
def create_admin_user(
    req: AdminUserCreateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=req.email,
        username=req.username,
        password_hash=hash_password(req.password),
        is_admin=req.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    settings = UserSettings(user_id=user.id)
    db.add(settings)
    db.commit()

    return AdminUserResponse.model_validate(user)


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
def update_user_role(
    user_id: int,
    req: AdminUserRoleUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_admin and not req.is_admin:
        # Prevent removing the last admin
        admin_count = db.query(User).filter(User.is_admin == True).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")

    user.is_admin = req.is_admin
    db.commit()
    db.refresh(user)
    return AdminUserResponse.model_validate(user)


# ─── Templates ─────────────────────────────────────
@router.get("/templates", response_model=list[TemplateListItem])
def list_templates(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    templates = db.query(Template).order_by(Template.updated_at.desc()).all()
    return [TemplateListItem.model_validate(t) for t in templates]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template_admin(
    template_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse.model_validate(tpl)


async def _run_template_generation(job_id: int, user_id: int):
    """Background coroutine that generates template slides one-by-one with SSE streaming."""
    db = SessionLocal()
    stream_manager.create_stream(job_id)

    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            stream_manager.push_event(job_id, "error", {"message": "Job not found"})
            return

        _update_job(db, job_id, status="running", stage="content_generation", progress=8, message="Starting AI template generation...")
        stream_manager.push_event(job_id, "stage", {
            "stage": "content_generation", "message": "Starting AI template generation...", "progress": 8,
        })

        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        groq_key = settings.groq_api_key if settings else ""
        openai_key = settings.openai_api_key if settings else ""
        selected_model = settings.selected_llm_model if settings else "groq/llama-3.3-70b-versatile"
        pexels_key = settings.pexels_api_key if settings else ""
        unsplash_key = settings.unsplash_access_key if settings else ""
        requested_slide_count = int(job.num_slides or 6)

        stream_manager.push_event(job_id, "theme", {
            "theme": {"name": "ocean-ink"},
            "title": _provisional_title_from_prompt(job.prompt or ""),
            "total_slides": requested_slide_count,
        })

        placeholder_stop = asyncio.Event()
        placeholder_task = asyncio.create_task(
            _stream_loading_slides(job_id, job.prompt or "", requested_slide_count, placeholder_stop)
        )

        _update_job(db, job_id, progress=15, message="Generating content structure...")
        stream_manager.push_event(job_id, "stage", {
            "stage": "content_generation", "message": "AI is crafting your template...", "progress": 15,
        })

        # Load user feedback rules for LLM improvement
        feedback_rules = get_feedback_rules_as_prompt(db, user_id)
        streamed_partial_indices: set[int] = set()

        async def _on_partial_slide(i: int, raw_slide: dict):
            if i < 0 or i >= requested_slide_count:
                return
            if i in streamed_partial_indices:
                return
            streamed_partial_indices.add(i)

            preview_pack = apply_auto_design(
                {"title": _provisional_title_from_prompt(job.prompt or ""), "theme": {"name": "ocean-ink"}, "slides": [raw_slide]},
                prompt=job.prompt or "",
                num_slides=1,
                slide_width=job.slide_width or 960,
                slide_height=job.slide_height or 540,
                is_template=True,
            )
            preview_slide = (preview_pack.get("slides") or [raw_slide])[0]
            vi = extract_visual(preview_slide)
            preview_data = build_slide_data(preview_slide, i, "", "", [], vi)
            stream_manager.push_event(job_id, "slide", {
                "index": i,
                "total": requested_slide_count,
                "placeholder": False,
                "from_llm_stream": True,
                "slide": preview_data,
            })

        llm_tick = 0
        async def _heartbeat():
            nonlocal llm_tick
            llm_tick += 1
            pulse_progress = min(28, 12 + llm_tick)
            pulse_msg = "AI is drafting template chunks..." if llm_tick % 2 else "AI is refining template structure..."
            _update_job(db, job_id, progress=pulse_progress, message=pulse_msg)
            stream_manager.push_event(job_id, "stage", {
                "stage": "content_generation",
                "message": pulse_msg,
                "progress": pulse_progress,
            })

        try:
            tpl, _usage = await _run_with_heartbeat(
                generate_template_content(
                    prompt=job.prompt,
                    num_slides=requested_slide_count,
                    groq_key=groq_key,
                    openai_key=openai_key,
                    model=selected_model,
                    slide_width=job.slide_width or 960,
                    slide_height=job.slide_height or 540,
                    feedback_rules=feedback_rules,
                    on_partial_slide=_on_partial_slide,
                ),
                _heartbeat,
                interval_s=1.1,
            )
            placeholder_stop.set()
            try:
                await placeholder_task
            except Exception:
                pass
        except ValueError as e:
            placeholder_stop.set()
            try:
                await placeholder_task
            except Exception:
                pass
            _update_job(db, job_id, status="failed", stage="failed", progress=0, error_detail=str(e))
            stream_manager.push_event(job_id, "error", {"message": str(e)})
            return
        except Exception as e:
            placeholder_stop.set()
            try:
                await placeholder_task
            except Exception:
                pass
            msg = f"Template generation failed: {str(e)}"
            _update_job(db, job_id, status="failed", stage="failed", progress=0, error_detail=msg)
            stream_manager.push_event(job_id, "error", {"message": msg})
            return

        usage_data = _usage or {}
        prompt_tokens = int(usage_data.get("prompt_tokens") or 0)
        completion_tokens = int(usage_data.get("completion_tokens") or 0)
        total_tokens = int(usage_data.get("total_tokens") or (prompt_tokens + completion_tokens))
        cost_usd = float(usage_data.get("cost_usd") or 0.0)
        model_used = usage_data.get("model") or selected_model

        tpl = apply_auto_design(
            tpl, prompt=job.prompt or "", num_slides=job.num_slides or 6,
            slide_width=job.slide_width or 960, slide_height=job.slide_height or 540, is_template=True,
        )

        _update_job(
            db, job_id, progress=30, message="Content generated",
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            total_tokens=total_tokens, model_used=model_used, cost_usd=cost_usd,
        )

        try:
            provider_name = (model_used or selected_model or "").split("/", 1)[0] or "unknown"
            token_record = TokenUsage(
                user_id=user_id, presentation_id=None, job_id=job_id, job_type="template",
                provider=provider_name, model=model_used,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                total_tokens=total_tokens, estimated_cost_usd=f"{cost_usd:.6f}", cost_usd=cost_usd,
            )
            db.add(token_record)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to save template token usage for job {job_id}: {e}")

        slides = tpl.get("slides", [])
        total_slide_count = len(slides)
        # Use LLM-returned theme directly instead of hardcoded choose_theme_id()
        custom_theme = tpl.get("theme", {})
        if not isinstance(custom_theme, dict):
            custom_theme = {"name": "ocean-ink"}

        # Send theme immediately
        stream_manager.push_event(job_id, "theme", {
            "theme": custom_theme,
            "title": tpl.get("title", "Untitled Template"),
            "total_slides": total_slide_count,
        })

        _update_job(db, job_id, stage="slide_building", progress=35, message="Building template slides...")
        stream_manager.push_event(job_id, "stage", {
            "stage": "slide_building", "message": "Building slides one by one...", "progress": 35,
        })

        # Process slides concurrently and stream replacements as each final slide completes
        template_slides: list[dict | None] = [None] * total_slide_count
        slide_progress_start = 35
        slide_progress_end = 92
        slide_progress_range = slide_progress_end - slide_progress_start
        completed_slides = 0
        per_job_semaphore = asyncio.Semaphore(SLIDE_BUILD_CONCURRENCY)
        asset_cache: dict[str, str] = {}

        async def resolve_image_url(query: str) -> str:
            cleaned = (query or "").strip()
            if not cleaned:
                return ""
            if cleaned in asset_cache:
                return asset_cache[cleaned]
            label_match = find_best_asset_url(db, cleaned)
            if label_match:
                asset_cache[cleaned] = label_match
                return label_match
            async with _global_media_fetch_semaphore:
                resolved = await fetch_image_with_fallback(cleaned, pexels_key, unsplash_key)
            asset_cache[cleaned] = resolved or ""
            return resolved or ""

        async def build_one_slide(i: int, slide: dict) -> tuple[int, dict]:
            async with per_job_semaphore:
                try:
                    vi = extract_visual(slide)
                    fg_task = resolve_image_url(vi.get("image_query", "education template background"))
                    bg_query = (slide.get("background_image_query") or "").strip()

                    async def _empty():
                        return ""

                    bg_task = resolve_image_url(bg_query) if bg_query else _empty()
                    icon_queries = vi.get("icon_queries", [])[:2]
                    icon_tasks_list = [search_iconify_icon(q) for q in icon_queries] if icon_queries else []

                    results = await asyncio.gather(fg_task, bg_task, *icon_tasks_list, return_exceptions=True)
                    image_url = results[0] if not isinstance(results[0], Exception) else ""
                    bg_image = results[1] if not isinstance(results[1], Exception) else ""
                    icon_names = [r for r in results[2:] if isinstance(r, str) and r]
                    slide_data = build_slide_data(slide, i, image_url, bg_image, icon_names, vi)
                    return i, slide_data
                except Exception as e:
                    logger.warning(f"Template slide build failed for job {job_id}, slide {i + 1}: {e}")
                    return i, _loading_slide(i, total_slide_count, job.prompt or "")

        tasks = [asyncio.create_task(build_one_slide(i, slide)) for i, slide in enumerate(slides)]
        for finished in asyncio.as_completed(tasks):
            i, slide_data = await finished
            template_slides[i] = slide_data
            completed_slides += 1
            slide_progress = slide_progress_start + int(
                (completed_slides / max(total_slide_count, 1)) * slide_progress_range
            )
            _update_job(
                db,
                job_id,
                progress=slide_progress,
                message=f"Built {completed_slides}/{total_slide_count} template slides...",
            )
            stream_manager.push_event(job_id, "slide", {
                "index": i,
                "total": total_slide_count,
                "placeholder": False,
                "slide": slide_data,
            })

        for i in range(total_slide_count):
            if template_slides[i] is None:
                template_slides[i] = _loading_slide(i, total_slide_count, job.prompt or "")

        # Save to database
        _update_job(db, job_id, stage="saving", progress=95, message="Saving template...")
        stream_manager.push_event(job_id, "stage", {
            "stage": "saving", "message": "Saving your template...", "progress": 95,
        })

        content = PresentationContent(
            title=tpl.get("title", "Untitled Template"),
            theme=custom_theme,
            slides=[SlideData(**s) for s in template_slides],
        )

        thumbnail = None
        for s in template_slides:
            if s.get("image_url"):
                thumbnail = s["image_url"]
                break

        template = Template(
            created_by=user_id, title=content.title,
            content_json=json.dumps(content.model_dump()),
            thumbnail_url=thumbnail, status="draft",
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        _update_job(
            db, job_id, status="completed", stage="done", progress=100,
            template_id=template.id, message="Template generated successfully",
        )
        stream_manager.push_event(job_id, "complete", {
            "template_id": template.id, "title": content.title, "total_slides": len(template_slides),
        })

    except Exception as e:
        logger.exception(f"Template generation job {job_id} failed unexpectedly")
        _update_job(db, job_id, status="failed", stage="failed", progress=0, error_detail=f"Unexpected error: {str(e)}")
        stream_manager.push_event(job_id, "error", {"message": f"Unexpected error: {str(e)}"})
    finally:
        stream_manager.close_stream(job_id)
        db.close()


@router.post("/templates/generate", response_model=GenerationJobResponse)
async def generate_template(
    req: TemplateGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(req.prompt) > 5000:
        raise HTTPException(status_code=400, detail="Prompt is too long (max 5000 characters)")

    job = GenerationJob(
        user_id=current_user.id,
        job_type="template",
        status="queued",
        stage="queued",
        progress=0,
        prompt=req.prompt.strip(),
        num_slides=req.num_slides or 6,
        slide_width=req.slide_width or 960,
        slide_height=req.slide_height or 540,
        message="Queued for generation...",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_template_generation, job.id, current_user.id)
    return GenerationJobResponse.model_validate(job)


@router.get("/templates/generate/{job_id}", response_model=GenerationJobResponse)
def get_template_generation_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    job = db.query(GenerationJob).filter(
        GenerationJob.id == job_id,
        GenerationJob.user_id == current_user.id,
        GenerationJob.job_type == "template",
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return GenerationJobResponse.model_validate(job)


@router.get("/templates/generate/{job_id}/stream")
async def stream_template_generation(
    job_id: int,
    request: Request,
    token: str = Query(..., description="JWT auth token"),
    last_event: int = Query(0, ge=0, description="Last event index for reconnection"),
):
    """SSE endpoint: streams slide-by-slide template generation events."""
    db = SessionLocal()
    try:
        user = _authenticate_from_token(token, db)
        if not user or not getattr(user, "is_admin", False):
            raise HTTPException(status_code=401, detail="Invalid token or not admin")

        job = db.query(GenerationJob).filter(
            GenerationJob.id == job_id,
            GenerationJob.user_id == user.id,
            GenerationJob.job_type == "template",
        ).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    finally:
        db.close()

    async def event_generator():
        try:
            for _ in range(50):
                if stream_manager.has_stream(job_id):
                    break
                await asyncio.sleep(0.1)

            if not stream_manager.has_stream(job_id):
                dbs = SessionLocal()
                try:
                    j = dbs.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                    if j and j.status == "completed" and j.template_id:
                        yield f"event: complete\ndata: {json.dumps({'template_id': j.template_id, 'title': '', 'total_slides': 0})}\n\n"
                    elif j and j.status == "failed":
                        yield f"event: error\ndata: {json.dumps({'message': j.error_detail or 'Generation failed'})}\n\n"
                    else:
                        yield f"event: error\ndata: {json.dumps({'message': 'Stream not available yet. Please retry.'})}\n\n"
                finally:
                    dbs.close()
                return

            async for event_type, data in stream_manager.subscribe(job_id, last_event):
                if await request.is_disconnected():
                    return
                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                if event_type in ("complete", "error"):
                    return

        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"SSE stream error for template job {job_id}: {e}")
            yield f"event: error\ndata: {json.dumps({'message': 'Stream error'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/templates/blank", response_model=TemplateResponse)
def create_blank_template(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    content = PresentationContent(
        title="Untitled Template",
        slides=[
            SlideData(
                heading="Title: {{Topic}}",
                points=["Student: {{StudentName}}", "Class: {{Class}}", "Division: {{Division}}"],
                description="School: {{SchoolName}}",
                image_query="colorful classroom background",
                image_url="",
                bg_color="#1a1a2e",
                text_color="#ffffff",
                layout="template",
            ),
            SlideData(
                heading="Section: {{SectionTitle}}",
                points=["Point 1", "Point 2", "Point 3"],
                description="Notes here",
                image_query="education icons",
                image_url="",
                bg_color="#1a1a2e",
                text_color="#ffffff",
                layout="template",
            ),
        ],
    )

    template = Template(
        created_by=current_user.id,
        title=content.title,
        content_json=json.dumps(content.model_dump()),
        status="draft",
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return TemplateResponse.model_validate(template)


@router.post("/templates/{template_id}/publish", response_model=TemplateResponse)
def publish_template(
    template_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    tpl.status = "published"
    db.commit()
    db.refresh(tpl)
    return TemplateResponse.model_validate(tpl)


@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    req: TemplateUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    if req.title is not None:
        tpl.title = req.title
    if req.content_json is not None:
        try:
            json.loads(req.content_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON content")
        tpl.content_json = req.content_json
    if req.thumbnail_url is not None:
        tpl.thumbnail_url = req.thumbnail_url

    db.commit()
    db.refresh(tpl)
    return TemplateResponse.model_validate(tpl)


@router.post("/templates/{template_id}/unpublish", response_model=TemplateResponse)
def unpublish_template(
    template_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    tpl.status = "draft"
    db.commit()
    db.refresh(tpl)
    return TemplateResponse.model_validate(tpl)


@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(tpl)
    db.commit()
    return {"message": "Template deleted"}


# ─── Assets ────────────────────────────────────────
from models import Asset

@router.get("/assets", response_model=list[AssetResponse])
def list_assets(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    assets = db.query(Asset).order_by(Asset.created_at.desc()).all()
    return [AssetResponse.model_validate(a) for a in assets]


@router.post("/assets", response_model=AssetResponse)
def create_asset(
    req: AssetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    asset = Asset(
        uploader_id=current_user.id,
        url=req.url,
        label=req.label,
        asset_type=req.asset_type,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return AssetResponse.model_validate(asset)


@router.delete("/assets/{asset_id}")
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()
    return {"message": "Asset deleted"}
