import json
import base64
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Template, Presentation, User
from schemas import TemplateListItem, TemplateResponse, PresentationResponse
from auth import get_current_user

router = APIRouter(prefix="/api/templates", tags=["Templates"])


@router.get("", response_model=list[TemplateListItem])
def list_published_templates(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    templates = (
        db.query(Template)
        .filter(Template.status == "published")
        .order_by(Template.updated_at.desc())
        .all()
    )
    return [TemplateListItem.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    tpl = db.query(Template).filter(Template.id == template_id, Template.status == "published").first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse.model_validate(tpl)


@router.post("/{template_id}/use", response_model=PresentationResponse)
def use_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tpl = db.query(Template).filter(Template.id == template_id, Template.status == "published").first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    # Create a new presentation from template content
    thumbnail = tpl.thumbnail_url
    if not thumbnail:
        try:
            content = json.loads(tpl.content_json or "{}")
            slides = content.get("slides") or []
            if slides:
                first = slides[0] or {}
                thumbnail = first.get("image_url") or ""
                if not thumbnail:
                    elements = first.get("_elements") or []
                    for el in elements:
                        if el.get("type") == "image" and el.get("src"):
                            thumbnail = el.get("src")
                            break
                if not thumbnail:
                    bg = first.get("bg_color") or "#1a1a2e"
                    title = (content.get("title") or tpl.title or "Template").strip()
                    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    svg = (
                        "<svg xmlns='http://www.w3.org/2000/svg' width='960' height='540'>"
                        f"<rect width='960' height='540' fill='{bg}'/>"
                        f"<text x='60' y='120' fill='#ffffff' font-size='48' font-family='Arial, sans-serif'>"
                        f"{safe_title[:40]}</text></svg>"
                    )
                    thumbnail = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("utf-8")
        except json.JSONDecodeError:
            thumbnail = tpl.thumbnail_url

    ppt = Presentation(
        user_id=current_user.id,
        title=tpl.title,
        content_json=tpl.content_json,
        thumbnail_url=thumbnail,
    )
    db.add(ppt)
    db.commit()
    db.refresh(ppt)
    return PresentationResponse.model_validate(ppt)
