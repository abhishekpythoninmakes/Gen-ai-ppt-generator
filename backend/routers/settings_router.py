from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserSettings, TokenUsage, GenerationJob
from schemas import SettingsRequest, SettingsResponse, TokenUsageResponse, UsageSummaryResponse
from auth import get_current_user
from datetime import datetime, timedelta, timezone
from config import DEFAULT_OPENAI_MODEL

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _mask_key(key: str) -> str:
    """Mask API key for display — show first 4 and last 4 chars."""
    if not key or len(key) < 12:
        return key
    return key[:4] + "•" * (len(key) - 8) + key[-4:]


def _as_utc(dt: datetime | None) -> datetime | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_model(model: str | None) -> str:
    value = (model or "").strip()
    if not value:
        return DEFAULT_OPENAI_MODEL
    if value.startswith("openai/"):
        return value
    if any(value.startswith(prefix) for prefix in ("gpt-", "o1", "o3")):
        return f"openai/{value}"
    return DEFAULT_OPENAI_MODEL


def _collect_usage_records(db: Session, user_id: int) -> list[dict]:
    """Collect usage records from token_usage with generation_jobs as fallback."""
    usage_rows = (
        db.query(TokenUsage)
        .filter(TokenUsage.user_id == user_id)
        .order_by(TokenUsage.created_at.desc())
        .all()
    )

    records: list[dict] = []
    seen_job_ids: set[int] = set()

    for row in usage_rows:
        if row.job_id:
            seen_job_ids.add(row.job_id)
        prompt_tokens = int(row.prompt_tokens or 0)
        completion_tokens = int(row.completion_tokens or 0)
        total_tokens = int(row.total_tokens or (prompt_tokens + completion_tokens))
        records.append(
            {
                "id": int(row.id),
                "job_type": row.job_type or "ppt",
                "provider": getattr(row, "provider", None) or "unknown",
                "model": row.model or "unknown",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": float(row.cost_usd or 0.0),
                "created_at": _as_utc(row.created_at) or datetime.now(timezone.utc),
            }
        )

    fallback_jobs = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.user_id == user_id,
            GenerationJob.status == "completed",
        )
        .order_by(GenerationJob.updated_at.desc())
        .all()
    )

    for job in fallback_jobs:
        if job.id in seen_job_ids:
            continue
        prompt_tokens = int(job.prompt_tokens or 0)
        completion_tokens = int(job.completion_tokens or 0)
        total_tokens = int(job.total_tokens or (prompt_tokens + completion_tokens))
        cost_usd = float(job.cost_usd or 0.0)
        if total_tokens <= 0 and cost_usd <= 0:
            continue

        records.append(
            {
                "id": 1_000_000_000 + int(job.id),
                "job_type": job.job_type or "ppt",
                "provider": (job.model_used or "unknown").split("/", 1)[0] if (job.model_used or "").strip() else "unknown",
                "model": job.model_used or "unknown",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "created_at": _as_utc(job.updated_at or job.created_at) or datetime.now(timezone.utc),
            }
        )

    records.sort(key=lambda r: r["created_at"], reverse=True)
    return records


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id, selected_llm_model=DEFAULT_OPENAI_MODEL)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return SettingsResponse(
        openai_api_key=_mask_key(settings.openai_api_key or ""),
        selected_llm_model=_normalize_model(settings.selected_llm_model),
        pexels_api_key=_mask_key(settings.pexels_api_key or ""),
        unsplash_access_key=_mask_key(settings.unsplash_access_key or ""),
        unsplash_secret_key=_mask_key(settings.unsplash_secret_key or ""),
    )


@router.post("", response_model=SettingsResponse)
def update_settings(
    req: SettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = db.query(UserSettings).filter(UserSettings.user_id == current_user.id).first()
    if not settings:
        settings = UserSettings(user_id=current_user.id, selected_llm_model=DEFAULT_OPENAI_MODEL)
        db.add(settings)

    if req.openai_api_key is not None and "•" not in (req.openai_api_key or ""):
        settings.openai_api_key = req.openai_api_key.strip()
    if req.selected_llm_model is not None:
        settings.selected_llm_model = _normalize_model(req.selected_llm_model)
    if req.pexels_api_key is not None and "•" not in (req.pexels_api_key or ""):
        settings.pexels_api_key = req.pexels_api_key.strip()
    if req.unsplash_access_key is not None and "•" not in (req.unsplash_access_key or ""):
        settings.unsplash_access_key = req.unsplash_access_key.strip()
    if req.unsplash_secret_key is not None and "•" not in (req.unsplash_secret_key or ""):
        settings.unsplash_secret_key = req.unsplash_secret_key.strip()

    db.commit()
    db.refresh(settings)

    return SettingsResponse(
        openai_api_key=_mask_key(settings.openai_api_key or ""),
        selected_llm_model=_normalize_model(settings.selected_llm_model),
        pexels_api_key=_mask_key(settings.pexels_api_key or ""),
        unsplash_access_key=_mask_key(settings.unsplash_access_key or ""),
        unsplash_secret_key=_mask_key(settings.unsplash_secret_key or ""),
    )


# ─── Token Usage Endpoints ────────────────────────────────────

@router.get("/usage", response_model=list[TokenUsageResponse])
def get_usage_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent token usage records for the current user."""
    records = _collect_usage_records(db, current_user.id)[:100]
    return [TokenUsageResponse.model_validate(r) for r in records]


@router.get("/usage/summary", response_model=UsageSummaryResponse)
def get_usage_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated token usage stats for the current user."""
    records = _collect_usage_records(db, current_user.id)

    total_tokens = sum(int(r.get("total_tokens") or 0) for r in records)
    total_cost = sum(float(r.get("cost_usd") or 0.0) for r in records)
    total_generations = len(records)

    # Per-model breakdown
    model_map = {}
    for r in records:
        model_name = r.get("model") or "unknown"
        if model_name not in model_map:
            model_map[model_name] = {
                "model": model_name,
                "count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
            }
        model_map[model_name]["count"] += 1
        model_map[model_name]["prompt_tokens"] += int(r.get("prompt_tokens") or 0)
        model_map[model_name]["completion_tokens"] += int(r.get("completion_tokens") or 0)
        model_map[model_name]["total_tokens"] += int(r.get("total_tokens") or 0)
        model_map[model_name]["cost_usd"] += float(r.get("cost_usd") or 0.0)

    by_model = sorted(model_map.values(), key=lambda x: x["cost_usd"], reverse=True)

    # Daily breakdown (last 30 days)
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=30)
    daily_map = {}
    for r in records:
        created_at = _as_utc(r.get("created_at"))
        if created_at and created_at >= cutoff:
            day_key = created_at.strftime("%Y-%m-%d")
            if day_key not in daily_map:
                daily_map[day_key] = {"date": day_key, "tokens": 0, "cost": 0.0, "count": 0}
            daily_map[day_key]["tokens"] += int(r.get("total_tokens") or 0)
            daily_map[day_key]["cost"] += float(r.get("cost_usd") or 0.0)
            daily_map[day_key]["count"] += 1

    # Fill in missing days
    daily = []
    for i in range(30):
        day = (now_utc - timedelta(days=29 - i)).strftime("%Y-%m-%d")
        if day in daily_map:
            daily.append(daily_map[day])
        else:
            daily.append({"date": day, "tokens": 0, "cost": 0.0, "count": 0})

    return UsageSummaryResponse(
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 4),
        total_generations=total_generations,
        by_model=by_model,
        daily=daily,
    )
