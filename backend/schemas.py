from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, Any
from datetime import datetime
import re


# ─── Auth Schemas ─────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username must be less than 50 characters")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        return v


class LoginRequest(BaseModel):
    identifier: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_admin: bool = False

    class Config:
        from_attributes = True


# ─── PPT Schemas ──────────────────────────────────────────────
class SlideStat(BaseModel):
    label: str = ""
    value: str = ""
    unit: str = ""
    note: str = ""


class SlideContent(BaseModel):
    heading: str = ""
    subheading: str = ""
    bullet_points: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    stats: list[SlideStat] = Field(default_factory=list)


class VisualElements(BaseModel):
    image_query: str = ""
    icon_query: list[str] = Field(default_factory=list)
    shape_type: list[str] = Field(default_factory=list)


class SlideData(BaseModel):
    heading: str = ""
    points: list[str] = Field(default_factory=list)
    description: str = ""
    image_query: str = ""
    image_url: str = ""
    bg_image: str = ""
    bg_color: str = "#1a1a2e"
    text_color: str = "#ffffff"
    font_family: str = "Inter"
    font_size: str = "24px"
    alignment: str = "left"
    layout: str = "default"
    icon_names: list[str] = Field(default_factory=list)
    slide_type: str = ""
    title: str = ""
    content: SlideContent = Field(default_factory=SlideContent)
    visual_elements: VisualElements = Field(default_factory=VisualElements)
    # Enhanced design fields
    background_image_query: str = ""
    overlay_opacity: float = 0.0
    text_placement_zone: str = "left"
    content_density: str = "balanced"
    design_notes: str = ""
    transition: dict = Field(default_factory=lambda: {"type": "fade", "duration": 0.5})


class PresentationContent(BaseModel):
    title: str = "Untitled Presentation"
    theme: dict | str = Field(default_factory=dict)
    slides: list[SlideData] = Field(default_factory=list)


class GeneratePPTRequest(BaseModel):
    prompt: str
    num_slides: int = Field(default=6, ge=1, le=30)
    slide_width: Optional[int] = 960
    slide_height: Optional[int] = 540


class PresentationResponse(BaseModel):
    id: int
    title: str
    content_json: str
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PresentationListItem(BaseModel):
    id: int
    title: str
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdatePresentationRequest(BaseModel):
    title: Optional[str] = None
    content_json: Optional[str] = None
    thumbnail_url: Optional[str] = None


# ─── Settings Schemas ─────────────────────────────────────────
class SettingsRequest(BaseModel):
    groq_api_key: Optional[str] = ""
    openai_api_key: Optional[str] = ""
    selected_llm_model: Optional[str] = "groq/llama-3.3-70b-versatile"
    pexels_api_key: Optional[str] = ""
    unsplash_access_key: Optional[str] = ""
    unsplash_secret_key: Optional[str] = ""


class SettingsResponse(BaseModel):
    groq_api_key: str = ""
    openai_api_key: str = ""
    selected_llm_model: str = "groq/llama-3.3-70b-versatile"
    pexels_api_key: str = ""
    unsplash_access_key: str = ""
    unsplash_secret_key: str = ""

    class Config:
        from_attributes = True


# ─── Generation Job Schemas ───────────────────────────────────
class GenerationJobResponse(BaseModel):
    id: int
    status: str
    stage: str
    progress: int
    message: str = ""
    ppt_id: Optional[int] = None
    template_id: Optional[int] = None
    error_detail: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_used: str = ""
    cost_usd: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Token Usage Schemas ──────────────────────────────────────
class TokenUsageResponse(BaseModel):
    id: int
    job_type: str = "ppt"
    provider: str = "unknown"
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    created_at: datetime

    class Config:
        from_attributes = True


class UsageSummaryResponse(BaseModel):
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_generations: int = 0
    by_model: list[dict] = Field(default_factory=list)
    daily: list[dict] = Field(default_factory=list)


# ─── Image Search Schema ─────────────────────────────────────
class ImageSearchRequest(BaseModel):
    query: str
    page: int = 1
    per_page: int = 4


class AssetPublicResponse(BaseModel):
    id: int
    url: str
    label: str
    asset_type: str

    class Config:
        from_attributes = True


# ─── Admin/User Schemas ─────────────────────────────────────
class AdminUserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AdminUserCreateRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    is_admin: bool = True


class AdminUserRoleUpdateRequest(BaseModel):
    is_admin: bool


# ─── Template Schemas ───────────────────────────────────────
class TemplateResponse(BaseModel):
    id: int
    title: str
    content_json: str
    thumbnail_url: Optional[str] = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateListItem(BaseModel):
    id: int
    title: str
    thumbnail_url: Optional[str] = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateGenerateRequest(BaseModel):
    prompt: str
    num_slides: int = Field(default=6, ge=1, le=30)
    slide_width: Optional[int] = 960
    slide_height: Optional[int] = 540


class TemplateUpdateRequest(BaseModel):
    title: Optional[str] = None
    content_json: Optional[str] = None
    thumbnail_url: Optional[str] = None


# ─── Feedback Schemas ────────────────────────────────────────
class FeedbackSubmitRequest(BaseModel):
    job_id: Optional[int] = None
    job_type: str = "ppt"  # ppt or template
    prompt_text: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_text: Optional[str] = None
    improvement_suggestions: Optional[str] = None
    what_was_good: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    rating: Optional[int] = None
    feedback_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackRulesResponse(BaseModel):
    rules: list[dict] = Field(default_factory=list)
    total_feedback_count: int = 0
    last_updated: Optional[str] = None
