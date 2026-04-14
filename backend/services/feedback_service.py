"""
Feedback service — analyzes user feedback using LLM, extracts design improvement rules,
and stores them as compact JSON for efficient context injection in future generations.

The rules are NOT every piece of feedback verbatim — they are LLM-summarized patterns
of what to improve, weighted by frequency and relevance.
"""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import UserFeedback, UserSettings

logger = logging.getLogger(__name__)

# Maximum rules to keep (prevents context bloat)
MAX_RULES = 20
MAX_RULE_TEXT_LENGTH = 100


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    """
    Normalize a datetime to timezone-aware UTC.
    SQLite often returns naive datetimes even when UTC values were written.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def save_feedback(
    db: Session,
    user_id: int,
    job_id: int | None,
    job_type: str,
    prompt_text: str | None,
    rating: int | None,
    feedback_text: str | None,
    improvement_suggestions: str | None,
    what_was_good: str | None,
) -> UserFeedback:
    """Save a feedback entry from the user."""
    feedback = UserFeedback(
        user_id=user_id,
        job_id=job_id,
        job_type=job_type,
        prompt_text=prompt_text,
        rating=rating,
        feedback_text=feedback_text,
        improvement_suggestions=improvement_suggestions,
        what_was_good=what_was_good,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback_rules(db: Session, user_id: int) -> dict:
    """Get the current compressed feedback rules for a user."""
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if not settings or not settings.feedback_rules_json:
        return {"rules": [], "total_feedback_count": 0, "last_updated": None}
    try:
        return json.loads(settings.feedback_rules_json)
    except (json.JSONDecodeError, TypeError):
        return {"rules": [], "total_feedback_count": 0, "last_updated": None}


def get_feedback_rules_as_prompt(db: Session, user_id: int) -> str:
    """
    Get feedback rules formatted as a string for injection into the LLM system prompt.
    Returns empty string if no rules exist.
    """
    rules_data = get_feedback_rules(db, user_id)
    rules = rules_data.get("rules", [])
    if not rules:
        return ""

    lines = []
    for rule in rules[:MAX_RULES]:
        context = rule.get("context", "general")
        improve = rule.get("improve", "")
        weight = rule.get("weight", 1)
        if improve:
            priority = "HIGH PRIORITY" if weight >= 3 else "MEDIUM" if weight >= 2 else ""
            prefix = f"[{priority}] " if priority else ""
            lines.append(f"- {prefix}For {context} presentations: {improve}")

    return "\n".join(lines)


def analyze_and_update_rules(
    db: Session,
    user_id: int,
    new_feedback: UserFeedback,
) -> dict:
    """
    Analyze new feedback and update the compressed rules.
    Uses simple NLP heuristics (no LLM call) to extract improvement patterns
    and merge with existing rules. This keeps it fast and free.
    """
    current_rules = get_feedback_rules(db, user_id)
    rules = current_rules.get("rules", [])
    total_count = current_rules.get("total_feedback_count", 0) + 1

    # Only process if there's actual improvement suggestions
    improvement = (new_feedback.improvement_suggestions or "").strip()
    feedback_text = (new_feedback.feedback_text or "").strip()
    prompt = (new_feedback.prompt_text or "").strip().lower()

    if not improvement and not feedback_text:
        # No meaningful feedback to analyze
        current_rules["total_feedback_count"] = total_count
        current_rules["last_updated"] = datetime.now(timezone.utc).isoformat()
        _save_rules(db, user_id, current_rules)
        return current_rules

    # Determine context from the prompt
    context = _detect_feedback_context(prompt)

    # Extract improvement points
    new_improvements = _extract_improvements(improvement, feedback_text)

    # Merge with existing rules
    for imp in new_improvements:
        merged = False
        for existing in rules:
            if existing.get("context") == context and _similar(existing.get("improve", ""), imp):
                # Increase weight of matching rule
                existing["weight"] = min(existing.get("weight", 1) + 1, 10)
                merged = True
                break
        if not merged and imp:
            rules.append({
                "context": context,
                "improve": imp[:MAX_RULE_TEXT_LENGTH],
                "weight": 1,
            })

    # Sort by weight (most important first) and cap
    rules.sort(key=lambda r: r.get("weight", 0), reverse=True)
    rules = rules[:MAX_RULES]

    # Remove low-weight rules if we're at capacity
    if len(rules) > MAX_RULES - 5:
        rules = [r for r in rules if r.get("weight", 0) >= 2] + \
                [r for r in rules if r.get("weight", 0) < 2][:5]

    updated = {
        "rules": rules,
        "total_feedback_count": total_count,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    _save_rules(db, user_id, updated)
    return updated


def _save_rules(db: Session, user_id: int, rules_data: dict):
    """Persist rules to user settings."""
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    if settings:
        settings.feedback_rules_json = json.dumps(rules_data, ensure_ascii=False)
        db.commit()


def _detect_feedback_context(prompt: str) -> str:
    """Simple context detection from the prompt text."""
    text = prompt.lower()
    if any(kw in text for kw in ["kids", "children", "class 1", "class 2", "class 3", "primary", "kindergarten"]):
        return "kids"
    if any(kw in text for kw in ["business", "corporate", "investor", "pitch", "finance"]):
        return "professional"
    if any(kw in text for kw in ["university", "research", "academic", "thesis"]):
        return "academic"
    if any(kw in text for kw in ["creative", "story", "art", "design", "portfolio"]):
        return "creative"
    return "general"


def _extract_improvements(improvement_text: str, feedback_text: str) -> list[str]:
    """Extract discrete improvement points from feedback text."""
    combined = f"{improvement_text} {feedback_text}".strip()
    if not combined:
        return []

    # Split by common separators
    points = []
    for sep in ["\n", ".", ";", ","]:
        if sep in combined:
            parts = combined.split(sep)
            points = [p.strip() for p in parts if len(p.strip()) > 10]
            if points:
                break

    if not points:
        points = [combined[:MAX_RULE_TEXT_LENGTH]]

    # Clean and filter
    cleaned = []
    for p in points:
        p = p.strip().rstrip(".")
        if len(p) > 10 and len(p) <= MAX_RULE_TEXT_LENGTH:
            cleaned.append(p)
        elif len(p) > MAX_RULE_TEXT_LENGTH:
            cleaned.append(p[:MAX_RULE_TEXT_LENGTH])

    return cleaned[:5]  # Max 5 improvements per feedback


def _similar(a: str, b: str) -> bool:
    """Simple similarity check between two improvement strings."""
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return False
    overlap = len(a_words & b_words)
    return overlap / max(len(a_words), len(b_words)) > 0.5


def should_ask_for_feedback(db: Session, user_id: int) -> bool:
    """
    Determine if we should ask the user for feedback.
    Uses randomization + frequency check to avoid being annoying.
    Returns True ~25-30% of the time, but never consecutively.
    """
    import random

    # Get recent feedback count
    recent_count = (
        db.query(UserFeedback)
        .filter(UserFeedback.user_id == user_id)
        .count()
    )

    # Don't ask for first generation (let them experience the tool first)
    if recent_count == 0:
        return random.random() < 0.15  # 15% chance on first use

    # Check last feedback time
    last_feedback = (
        db.query(UserFeedback)
        .filter(UserFeedback.user_id == user_id)
        .order_by(UserFeedback.created_at.desc())
        .first()
    )

    if last_feedback:
        now = datetime.now(timezone.utc)
        last_created_at = _as_utc_aware(last_feedback.created_at)
        if last_created_at is not None:
            time_since_last = (now - last_created_at).total_seconds()
        else:
            time_since_last = 999999
        # Don't ask if last feedback was less than 10 minutes ago
        if time_since_last < 600:
            return False

    # Random 25-30% chance
    return random.random() < 0.28
