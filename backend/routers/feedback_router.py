"""
Feedback router — handles user feedback submission and rules retrieval.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import FeedbackSubmitRequest, FeedbackResponse, FeedbackRulesResponse
from auth import get_current_user
from services.feedback_service import (
    save_feedback,
    get_feedback_rules,
    analyze_and_update_rules,
    should_ask_for_feedback,
)

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    req: FeedbackSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback for a generated presentation or template."""
    feedback = save_feedback(
        db=db,
        user_id=current_user.id,
        job_id=req.job_id,
        job_type=req.job_type,
        prompt_text=req.prompt_text,
        rating=req.rating,
        feedback_text=req.feedback_text,
        improvement_suggestions=req.improvement_suggestions,
        what_was_good=req.what_was_good,
    )

    # Analyze and update compressed rules
    analyze_and_update_rules(db, current_user.id, feedback)

    return FeedbackResponse.model_validate(feedback)


@router.get("/rules", response_model=FeedbackRulesResponse)
def get_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current compressed feedback rules for the user."""
    rules_data = get_feedback_rules(db, current_user.id)
    return FeedbackRulesResponse(**rules_data)


@router.get("/should-ask")
def check_should_ask(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if we should show the feedback popup to the user."""
    should_ask = should_ask_for_feedback(db, current_user.id)
    return {"should_ask": should_ask}
