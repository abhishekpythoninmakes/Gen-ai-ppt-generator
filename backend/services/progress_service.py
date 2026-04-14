from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from models import GenerationJob


def create_job(
    db: Session,
    user_id: int,
    job_type: str,
    status: str = "queued",
    stage: str = "queued",
    progress: int = 0,
    message: Optional[str] = None,
) -> GenerationJob:
    job = GenerationJob(
        user_id=user_id,
        job_type=job_type,
        status=status,
        stage=stage,
        progress=progress,
        message=message or "",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(db: Session, job_id: int, **fields) -> Optional[GenerationJob]:
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
