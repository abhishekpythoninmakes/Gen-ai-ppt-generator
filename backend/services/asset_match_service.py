import re
from difflib import SequenceMatcher
from typing import Iterable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import Asset


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 2]


def _score_label(query_terms: set[str], query_text: str, label: str) -> float:
    if not label:
        return 0.0
    label_text = label.lower().strip()
    label_terms = set(_tokenize(label_text))
    overlap = len(query_terms.intersection(label_terms))
    contains_bonus = 5.0 if query_text and query_text in label_text else 0.0
    ratio_bonus = SequenceMatcher(None, query_text, label_text).ratio() * 4.0 if query_text else 0.0
    return overlap * 8.0 + contains_bonus + ratio_bonus


def _iter_candidate_assets(db: Session, query: str, limit: int = 200) -> Iterable[Asset]:
    q = (query or "").strip()
    terms = _tokenize(q)[:4]
    rows = db.query(Asset).filter(Asset.url.isnot(None), Asset.url != "")
    if terms:
        rows = rows.filter(or_(*[Asset.label.ilike(f"%{t}%") for t in terms]))
    return rows.order_by(Asset.created_at.desc()).limit(max(1, min(limit, 500))).all()


def find_best_asset_url(db: Session, query: str) -> str:
    q = (query or "").strip().lower()
    if not q:
        return ""
    q_terms = set(_tokenize(q))
    if not q_terms:
        return ""

    best_url = ""
    best_score = 0.0
    for asset in _iter_candidate_assets(db, q):
        score = _score_label(q_terms, q, asset.label or "")
        if score > best_score:
            best_score = score
            best_url = asset.url or ""

    # Conservative threshold to avoid unrelated assets being injected.
    return best_url if best_score >= 8.5 else ""


def list_assets_for_editor(db: Session, query: str = "", limit: int = 100) -> list[Asset]:
    q = (query or "").strip()
    rows = db.query(Asset).filter(Asset.url.isnot(None), Asset.url != "")
    if q:
        rows = rows.filter(Asset.label.ilike(f"%{q}%"))
    return rows.order_by(Asset.created_at.desc()).limit(max(1, min(limit, 500))).all()

