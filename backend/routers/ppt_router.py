import json
import asyncio
import httpx
import logging
from typing import Awaitable, Callable, Any
from urllib.parse import quote_plus
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from database import get_db, SessionLocal
from models import User, Presentation, UserSettings, GenerationJob, TokenUsage
from schemas import (
    GeneratePPTRequest,
    PresentationResponse,
    PresentationListItem,
    UpdatePresentationRequest,
    PresentationContent,
    SlideData,
    ImageSearchRequest,
    GenerationJobResponse,
    AssetPublicResponse,
)
from auth import get_current_user
from config import SECRET_KEY, ALGORITHM
from services.llm_service import generate_ppt_content
from services.auto_design_service import apply_auto_design
from services.asset_match_service import find_best_asset_url, list_assets_for_editor
from services.image_service import fetch_image_with_fallback, fetch_images_with_fallback
from services.stream_manager import stream_manager
from services.feedback_service import get_feedback_rules_as_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ppt", tags=["Presentations"])

SLIDE_BUILD_CONCURRENCY = 4
GLOBAL_MEDIA_FETCH_CONCURRENCY = 16
_global_media_fetch_semaphore = asyncio.Semaphore(GLOBAL_MEDIA_FETCH_CONCURRENCY)


# ── Helpers ──────────────────────────────────────────────

def _update_job(db: Session, job_id: int, **fields):
    """Update a generation job's fields."""
    from datetime import datetime, timezone
    job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    if job:
        for k, v in fields.items():
            if hasattr(job, k):
                setattr(job, k, v)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()


def _authenticate_from_token(token: str, db: Session) -> User | None:
    """Verify JWT token from query param (for SSE EventSource which can't set headers)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        user_id = int(sub)
    except (JWTError, ValueError, TypeError):
        return None
    return db.query(User).filter(User.id == user_id).first()


def as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def as_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def normalize_stats(value) -> list[dict]:
    items = []
    if isinstance(value, dict):
        value = [value]
    if isinstance(value, (str, int, float)):
        value = [value]
    for item in value if isinstance(value, list) else []:
        if isinstance(item, dict):
            items.append({
                "label": str(item.get("label", "")).strip(),
                "value": str(item.get("value", "")).strip(),
                "unit": str(item.get("unit", "")).strip(),
                "note": str(item.get("note", "")).strip(),
            })
        elif isinstance(item, (str, int, float)):
            items.append({"label": str(item), "value": "", "unit": "", "note": ""})
    return items


def extract_visual(slide: dict) -> dict:
    visual = as_dict(slide.get("visual_elements"))
    image_query = slide.get("image_query") or visual.get("image_query") or "abstract background"
    icon_queries = as_list(
        slide.get("icon_query")
        or slide.get("icon_queries")
        or visual.get("icon_query")
        or visual.get("icon_queries")
    )
    icon_queries = [q for q in icon_queries if isinstance(q, str) and q.strip()]
    shape_type = as_list(slide.get("shape_type") or visual.get("shape_type"))
    return {
        "image_query": image_query,
        "icon_queries": icon_queries,
        "shape_type": shape_type,
    }


async def search_iconify_icon(query: str) -> str:
    if not query:
        return ""
    try:
        url = f"https://api.iconify.design/search?query={quote_plus(query)}&limit=1"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            icons = data.get("icons", [])
            return icons[0] if icons else ""
    except Exception:
        return ""


def build_slide_data(slide: dict, i: int, image_url: str, bg_image: str, icon_names: list, visual_info: dict) -> dict:
    """Build a single SlideData dict from processed slide data."""
    content = as_dict(slide.get("content"))
    heading = (
        content.get("heading")
        or slide.get("heading")
        or slide.get("title")
        or f"Slide {i + 1}"
    )
    points = as_list(content.get("bullet_points") or slide.get("points"))
    description = content.get("subheading") or slide.get("description") or ""
    steps = as_list(content.get("steps"))
    stats = normalize_stats(content.get("stats"))

    overlay_opacity = float(slide.get("overlay_opacity", 0.0)) if bg_image else 0.0

    return SlideData(
        heading=heading,
        points=points,
        description=description,
        image_query=visual_info.get("image_query", ""),
        image_url=image_url,
        bg_image=bg_image,
        icon_names=icon_names,
        slide_type=slide.get("slide_type", ""),
        layout=slide.get("layout", "default"),
        title=slide.get("title", ""),
        text_placement_zone=slide.get("text_placement_zone", "left"),
        content_density=slide.get("content_density", "balanced"),
        background_image_query=slide.get("background_image_query", ""),
        overlay_opacity=overlay_opacity,
        design_notes=slide.get("design_notes", ""),
        transition=slide.get("transition") or {"type": "fade", "duration": 0.5},
        content={
            "heading": heading,
            "subheading": description,
            "bullet_points": [str(p) for p in points if str(p).strip()],
            "steps": [str(s) for s in steps if str(s).strip()],
            "stats": stats,
        },
        visual_elements={
            "image_query": visual_info.get("image_query", ""),
            "icon_query": visual_info.get("icon_queries", []),
            "shape_type": visual_info.get("shape_type", []),
        },
    ).model_dump()


def _provisional_title_from_prompt(prompt: str) -> str:
    text = (prompt or "").strip()
    if not text:
        return "Generating Presentation..."
    words = [w for w in text.replace("\n", " ").split(" ") if w.strip()]
    head = " ".join(words[:6]).strip()
    return (head[:60] + "...") if len(head) > 60 else f"{head}..."


def _loading_slide(i: int, total: int, prompt: str = "") -> dict:
    return SlideData(
        heading=f"Preparing Slide {i + 1}",
        points=[
            "Drafting content outline",
            "Selecting visuals and icons",
            "Balancing layout and typography",
        ],
        description=f"Generating live ({i + 1}/{total})...",
        image_query="",
        image_url="",
        bg_image="",
        slide_type="content",
        layout="split",
        title=f"Slide {i + 1}",
        text_placement_zone="left",
        content_density="balanced",
        background_image_query="",
        overlay_opacity=0.0,
        design_notes="Temporary loading slide while AI prepares final content.",
        transition={"type": "fade", "duration": 0.4},
        content={
            "heading": f"Preparing Slide {i + 1}",
            "subheading": f"Generating live ({i + 1}/{total})...",
            "bullet_points": [
                "Drafting content outline",
                "Selecting visuals and icons",
                "Balancing layout and typography",
            ],
            "steps": [],
            "stats": [],
        },
        visual_elements={"image_query": "", "icon_query": [], "shape_type": ["circle"]},
    ).model_dump()


async def _run_with_heartbeat(
    awaitable: Awaitable,
    heartbeat: Callable[[], Awaitable[None]],
    interval_s: float = 1.2,
):
    task = asyncio.create_task(awaitable)
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=interval_s)
            if task in done:
                return await task
            await heartbeat()
    finally:
        if not task.done():
            task.cancel()


async def _stream_loading_slides(job_id: int, prompt: str, total: int, stop_event: asyncio.Event):
    """Emit lightweight scaffold slides quickly so users see immediate live activity."""
    idx = 0
    chunk_size = 2
    while idx < total and not stop_event.is_set():
        for _ in range(chunk_size):
            if idx >= total or stop_event.is_set():
                break
            stream_manager.push_event(job_id, "slide", {
                "index": idx,
                "total": total,
                "placeholder": True,
                "slide": _loading_slide(idx, total, prompt),
            })
            idx += 1
        await asyncio.sleep(0.15)


# ── Streaming Generation Pipeline ──────────────────────

async def _run_generation_streaming(job_id: int, user_id: int):
    """
    Background coroutine that generates PPT slides one-by-one,
    streaming each completed slide via the StreamManager event bus.
    """
    db = SessionLocal()
    stream_manager.create_stream(job_id)

    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            stream_manager.push_event(job_id, "error", {"message": "Job not found"})
            return

        _update_job(db, job_id, status="running", stage="content_generation", progress=5, message="Starting AI content generation...")
        stream_manager.push_event(job_id, "stage", {
            "stage": "content_generation",
            "message": "Starting AI content generation...",
            "progress": 5,
        })

        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        groq_key = settings.groq_api_key if settings else ""
        openai_key = settings.openai_api_key if settings else ""
        selected_model = settings.selected_llm_model if settings else "groq/llama-3.3-70b-versatile"
        pexels_key = settings.pexels_api_key if settings else ""
        unsplash_key = settings.unsplash_access_key if settings else ""
        requested_slide_count = int(job.num_slides or 6)

        # Push provisional theme/title immediately so editor can open fast.
        stream_manager.push_event(job_id, "theme", {
            "theme": {"name": "ocean-ink"},
            "title": _provisional_title_from_prompt(job.prompt or ""),
            "total_slides": requested_slide_count,
        })

        # Stream lightweight scaffold slides in chunks while LLM is still generating.
        placeholder_stop = asyncio.Event()
        placeholder_task = asyncio.create_task(
            _stream_loading_slides(job_id, job.prompt or "", requested_slide_count, placeholder_stop)
        )

        # ── Step 1: Generate ALL content via LLM ──
        _update_job(db, job_id, progress=10, message="Generating slide content with AI...")
        stream_manager.push_event(job_id, "stage", {
            "stage": "content_generation",
            "message": "AI is crafting your slides...",
            "progress": 10,
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

            # Normalize minimal content for immediate live rendering.
            preview_pack = apply_auto_design(
                {"title": _provisional_title_from_prompt(job.prompt or ""), "theme": {"name": "ocean-ink"}, "slides": [raw_slide]},
                prompt=job.prompt or "",
                num_slides=1,
                slide_width=job.slide_width or 960,
                slide_height=job.slide_height or 540,
                is_template=False,
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
            pulse_progress = min(28, 10 + llm_tick)
            pulse_msg = "AI is drafting slide chunks..." if llm_tick % 2 else "AI is refining structure..."
            _update_job(db, job_id, progress=pulse_progress, message=pulse_msg)
            stream_manager.push_event(job_id, "stage", {
                "stage": "content_generation",
                "message": pulse_msg,
                "progress": pulse_progress,
            })

        try:
            ai_content, usage_data = await _run_with_heartbeat(
                generate_ppt_content(
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
            msg = f"AI generation failed: {str(e)}"
            _update_job(db, job_id, status="failed", stage="failed", progress=0, error_detail=msg)
            stream_manager.push_event(job_id, "error", {"message": msg})
            return

        # Token usage tracking
        usage_data = usage_data or {}
        prompt_tokens = int(usage_data.get("prompt_tokens") or 0)
        completion_tokens = int(usage_data.get("completion_tokens") or 0)
        total_tokens = int(usage_data.get("total_tokens") or 0)
        cost_usd = float(usage_data.get("cost_usd") or 0.0)
        model_used = usage_data.get("model") or selected_model

        # Auto Design System
        ai_content = apply_auto_design(
            ai_content,
            prompt=job.prompt or "",
            num_slides=job.num_slides or 6,
            slide_width=job.slide_width or 960,
            slide_height=job.slide_height or 540,
            is_template=False,
        )

        # Store token usage on the job
        _update_job(
            db, job_id, progress=30, message="Content generated!",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model_used=model_used,
            cost_usd=cost_usd,
        )

        # Persist token usage record
        try:
            provider_name = (model_used or selected_model or "").split("/", 1)[0] or "unknown"
            token_record = TokenUsage(
                user_id=user_id,
                presentation_id=None,
                job_id=job_id,
                job_type="ppt",
                provider=provider_name,
                model=model_used,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=f"{cost_usd:.6f}",
                cost_usd=cost_usd,
            )
            db.add(token_record)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to save token usage for job {job_id}: {e}")

        slides = ai_content.get("slides", [])
        total_slide_count = len(slides)
        custom_theme = ai_content.get("theme", {})
        if not isinstance(custom_theme, dict):
            custom_theme = {"name": "ocean-ink"}

        # ── Step 2: Send theme immediately ──
        stream_manager.push_event(job_id, "theme", {
            "theme": custom_theme,
            "title": ai_content.get("title", "Untitled Presentation"),
            "total_slides": total_slide_count,
        })

        _update_job(db, job_id, stage="slide_building", progress=35, message="Building slides...")
        stream_manager.push_event(job_id, "stage", {
            "stage": "slide_building",
            "message": "Building slides one by one...",
            "progress": 35,
        })

        # ── Step 3: Process slides concurrently and stream as each one completes ──
        presentation_slides: list[dict | None] = [None] * total_slide_count
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

                    fg_task = resolve_image_url(vi.get("image_query", "abstract background"))
                    bg_query = (slide.get("background_image_query") or "").strip()

                    async def _empty():
                        return ""

                    bg_task = resolve_image_url(bg_query) if bg_query else _empty()
                    icon_queries = vi.get("icon_queries", [])[:2]
                    icon_tasks = [search_iconify_icon(q) for q in icon_queries] if icon_queries else []

                    results = await asyncio.gather(
                        fg_task,
                        bg_task,
                        *icon_tasks,
                        return_exceptions=True,
                    )

                    image_url = results[0] if not isinstance(results[0], Exception) else ""
                    bg_image = results[1] if not isinstance(results[1], Exception) else ""
                    icon_names = [r for r in results[2:] if isinstance(r, str) and r]
                    slide_data = build_slide_data(slide, i, image_url, bg_image, icon_names, vi)
                    return i, slide_data
                except Exception as e:
                    logger.warning(f"Slide build failed for job {job_id}, slide {i + 1}: {e}")
                    return i, _loading_slide(i, total_slide_count, job.prompt or "")

        tasks = [asyncio.create_task(build_one_slide(i, slide)) for i, slide in enumerate(slides)]

        for finished in asyncio.as_completed(tasks):
            i, slide_data = await finished
            presentation_slides[i] = slide_data
            completed_slides += 1
            slide_progress = slide_progress_start + int(
                (completed_slides / max(total_slide_count, 1)) * slide_progress_range
            )
            _update_job(
                db,
                job_id,
                progress=slide_progress,
                message=f"Built {completed_slides}/{total_slide_count} slides...",
            )
            stream_manager.push_event(job_id, "slide", {
                "index": i,
                "total": total_slide_count,
                "placeholder": False,
                "slide": slide_data,
            })

        # Backfill any failed slots (rare) to maintain exact count.
        for i in range(total_slide_count):
            if presentation_slides[i] is None:
                presentation_slides[i] = _loading_slide(i, total_slide_count, job.prompt or "")

        # ── Step 4: Save to database ──
        _update_job(db, job_id, stage="saving", progress=95, message="Saving presentation...")
        stream_manager.push_event(job_id, "stage", {
            "stage": "saving",
            "message": "Saving your presentation...",
            "progress": 95,
        })

        ppt_content = PresentationContent(
            title=ai_content.get("title", "Untitled Presentation"),
            theme=custom_theme,
            slides=[SlideData(**s) for s in presentation_slides],
        )

        thumbnail = None
        for s in presentation_slides:
            if s.get("image_url"):
                thumbnail = s["image_url"]
                break

        ppt = Presentation(
            user_id=user_id,
            title=ppt_content.title,
            content_json=json.dumps(ppt_content.model_dump()),
            thumbnail_url=thumbnail,
        )
        db.add(ppt)
        db.commit()
        db.refresh(ppt)

        # ── Step 5: Signal completion ──
        _update_job(
            db, job_id,
            status="completed", stage="done", progress=100,
            ppt_id=ppt.id, message="Done!",
        )

        stream_manager.push_event(job_id, "complete", {
            "ppt_id": ppt.id,
            "title": ppt_content.title,
            "total_slides": len(presentation_slides),
        })

        logger.info(f"Generation job {job_id} completed. PPT ID: {ppt.id}")

    except Exception as e:
        logger.exception(f"Generation job {job_id} failed unexpectedly")
        _update_job(db, job_id, status="failed", stage="failed", progress=0, error_detail=f"Unexpected error: {str(e)}")
        stream_manager.push_event(job_id, "error", {"message": f"Unexpected error: {str(e)}"})
    finally:
        stream_manager.close_stream(job_id)
        db.close()


# ── Routes ───────────────────────────────────────────────

@router.post("/generate", response_model=GenerationJobResponse)
async def generate_ppt(
    req: GeneratePPTRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start generating a new presentation (returns a job to poll or stream)."""
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(req.prompt) > 5000:
        raise HTTPException(status_code=400, detail="Prompt is too long (max 5000 characters)")

    job = GenerationJob(
        user_id=current_user.id,
        job_type="ppt",
        status="queued",
        stage="queued",
        progress=0,
        prompt=req.prompt.strip(),
        num_slides=req.num_slides,
        slide_width=req.slide_width or 960,
        slide_height=req.slide_height or 540,
        message="Queued for generation...",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_generation_streaming, job.id, current_user.id)
    return GenerationJobResponse.model_validate(job)


@router.get("/generate/{job_id}/stream")
async def stream_generation(
    job_id: int,
    request: Request,
    token: str = Query(..., description="JWT auth token"),
    last_event: int = Query(0, ge=0, description="Last event index for reconnection"),
):
    """
    SSE endpoint: streams slide-by-slide generation events.

    EventSource can't set headers, so auth is via query param ?token=<jwt>.
    Supports reconnection via ?last_event=<index>.
    """
    db = SessionLocal()
    try:
        user = _authenticate_from_token(token, db)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        job = db.query(GenerationJob).filter(
            GenerationJob.id == job_id,
            GenerationJob.user_id == user.id,
        ).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    finally:
        db.close()

    async def event_generator():
        keepalive_interval = 15  # seconds
        try:
            # Wait briefly for stream to be created if generation just started
            for _ in range(50):
                if stream_manager.has_stream(job_id):
                    break
                await asyncio.sleep(0.1)

            if not stream_manager.has_stream(job_id):
                # Stream may have already completed; check DB
                dbs = SessionLocal()
                try:
                    j = dbs.query(GenerationJob).filter(GenerationJob.id == job_id).first()
                    if j and j.status == "completed" and j.ppt_id:
                        yield f"event: complete\ndata: {json.dumps({'ppt_id': j.ppt_id, 'title': '', 'total_slides': 0})}\n\n"
                    elif j and j.status == "failed":
                        yield f"event: error\ndata: {json.dumps({'message': j.error_detail or 'Generation failed'})}\n\n"
                    else:
                        yield f"event: error\ndata: {json.dumps({'message': 'Stream not available yet. Please retry.'})}\n\n"
                finally:
                    dbs.close()
                return

            async for event_type, data in stream_manager.subscribe(job_id, last_event):
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.debug(f"Client disconnected from stream {job_id}")
                    return

                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

                if event_type in ("complete", "error"):
                    return

        except asyncio.CancelledError:
            logger.debug(f"Stream {job_id} cancelled (client disconnect)")
            return
        except Exception as e:
            logger.error(f"SSE stream error for job {job_id}: {e}")
            yield f"event: error\ndata: {json.dumps({'message': 'Stream error'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/generate/{job_id}", response_model=GenerationJobResponse)
def get_generation_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll the status of a generation job (fallback for non-SSE clients)."""
    job = db.query(GenerationJob).filter(
        GenerationJob.id == job_id,
        GenerationJob.user_id == current_user.id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return GenerationJobResponse.model_validate(job)


@router.get("/assets", response_model=list[AssetPublicResponse])
def list_editor_assets(
    q: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List admin-curated assets for editor selection and AI-assisted matching."""
    _ = current_user  # auth gate only
    rows = list_assets_for_editor(db, query=q, limit=limit)
    return [AssetPublicResponse.model_validate(a) for a in rows]


@router.get("/list", response_model=list[PresentationListItem])
def list_presentations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ppts = (
        db.query(Presentation)
        .filter(Presentation.user_id == current_user.id)
        .order_by(Presentation.updated_at.desc())
        .all()
    )
    return [PresentationListItem.model_validate(p) for p in ppts]


@router.get("/{ppt_id}", response_model=PresentationResponse)
def get_presentation(
    ppt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ppt = (
        db.query(Presentation)
        .filter(Presentation.id == ppt_id, Presentation.user_id == current_user.id)
        .first()
    )
    if not ppt:
        raise HTTPException(status_code=404, detail="Presentation not found")
    return PresentationResponse.model_validate(ppt)


@router.put("/{ppt_id}", response_model=PresentationResponse)
def update_presentation(
    ppt_id: int,
    req: UpdatePresentationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ppt = (
        db.query(Presentation)
        .filter(Presentation.id == ppt_id, Presentation.user_id == current_user.id)
        .first()
    )
    if not ppt:
        raise HTTPException(status_code=404, detail="Presentation not found")

    if req.title is not None:
        ppt.title = req.title
    if req.content_json is not None:
        try:
            json.loads(req.content_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON content")
        ppt.content_json = req.content_json
    if req.thumbnail_url is not None:
        ppt.thumbnail_url = req.thumbnail_url

    db.commit()
    db.refresh(ppt)
    return PresentationResponse.model_validate(ppt)


@router.delete("/{ppt_id}")
def delete_presentation(
    ppt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ppt = (
        db.query(Presentation)
        .filter(Presentation.id == ppt_id, Presentation.user_id == current_user.id)
        .first()
    )
    if not ppt:
        raise HTTPException(status_code=404, detail="Presentation not found")

    db.delete(ppt)
    db.commit()
    return {"message": "Presentation deleted successfully"}


@router.post("/blank", response_model=PresentationResponse)
def create_blank_presentation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = PresentationContent(
        title="Untitled Presentation",
        slides=[
            SlideData(
                heading="Welcome",
                points=["Click to edit this slide"],
                description="Your presentation starts here",
                image_query="",
                image_url="",
            ),
        ],
    )

    ppt = Presentation(
        user_id=current_user.id,
        title=content.title,
        content_json=json.dumps(content.model_dump()),
    )
    db.add(ppt)
    db.commit()
    db.refresh(ppt)

    return PresentationResponse.model_validate(ppt)


@router.post("/search-image")
async def search_image(
    req: ImageSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (req.query or "").strip()
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="Search query must have at least 2 characters")

    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    pexels_key = settings.pexels_api_key if settings else ""
    unsplash_key = settings.unsplash_access_key if settings else ""

    page = max(1, req.page or 1)
    per_page = min(max(1, req.per_page or 4), 12)

    from models import Asset
    offset = (page - 1) * per_page
    local_assets = (
        db.query(Asset)
        .filter(Asset.label.ilike(f"%{query}%"))
        .offset(offset)
        .limit(per_page)
        .all()
    )
    local_urls = [a.url for a in local_assets]

    # Keep external providers first so live search surfaces web image results,
    # then blend local assets.
    external_urls = await fetch_images_with_fallback(
        query,
        pexels_key,
        unsplash_key,
        page=page,
        per_page=per_page,
        allow_placeholder=False,
    )

    deduped: list[str] = []
    seen = set()
    for url in (external_urls + local_urls):
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(url)
        if len(deduped) >= per_page:
            break

    return {"image_urls": deduped, "query": query, "page": page, "per_page": per_page}
