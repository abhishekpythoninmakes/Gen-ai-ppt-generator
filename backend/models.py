from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    presentations = relationship("Presentation", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="creator", cascade="all, delete-orphan")


class Presentation(Base):
    __tablename__ = "presentations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False, default="Untitled Presentation")
    content_json = Column(Text, nullable=False, default="{}")
    thumbnail_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="presentations")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    openai_api_key = Column(String(500), nullable=True, default="")
    selected_llm_model = Column(String(100), nullable=True, default="openai/gpt-4o-mini")
    pexels_api_key = Column(String(500), nullable=True, default="")
    unsplash_access_key = Column(String(500), nullable=True, default="")
    unsplash_secret_key = Column(String(500), nullable=True, default="")
    feedback_rules_json = Column(Text, nullable=True, default="{}")


    user = relationship("User", back_populates="settings")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_type = Column(String(50), nullable=False, default="ppt")
    status = Column(String(20), nullable=False, default="queued")
    stage = Column(String(50), nullable=False, default="queued")
    progress = Column(Integer, nullable=False, default=0)
    message = Column(String(500), nullable=True, default="")
    ppt_id = Column(Integer, nullable=True)
    template_id = Column(Integer, nullable=True)
    error_detail = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)
    num_slides = Column(Integer, nullable=True, default=6)
    slide_width = Column(Integer, nullable=True, default=960)
    slide_height = Column(Integer, nullable=True, default=540)
    # Token tracking
    prompt_tokens = Column(Integer, nullable=True, default=0)
    completion_tokens = Column(Integer, nullable=True, default=0)
    total_tokens = Column(Integer, nullable=True, default=0)
    model_used = Column(String(100), nullable=True, default="")
    cost_usd = Column(Float, nullable=True, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    presentation_id = Column(Integer, ForeignKey("presentations.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("generation_jobs.id"), nullable=True)
    job_type = Column(String(50), nullable=False, default="ppt")
    provider = Column(String(50), nullable=False, default="unknown")
    model = Column(String(100), nullable=False, default="")
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(String(20), nullable=False, default="0.000000")
    cost_usd = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(500), nullable=False, default="Untitled Template")
    content_json = Column(Text, nullable=False, default="{}")
    thumbnail_url = Column(String(1000), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", back_populates="templates")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String(1000), nullable=False)
    label = Column(String(255), nullable=True, index=True)
    asset_type = Column(String(50), nullable=False, default="image")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    uploader = relationship("User")


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("generation_jobs.id"), nullable=True)
    job_type = Column(String(50), nullable=False, default="ppt")  # ppt or template
    prompt_text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    feedback_text = Column(Text, nullable=True)
    improvement_suggestions = Column(Text, nullable=True)
    what_was_good = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")

