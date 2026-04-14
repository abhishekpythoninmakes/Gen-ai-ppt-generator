import re
from typing import Any


TRANSITION_BY_TYPE = {
    "hero": {"type": "fade", "duration": 0.7},
    "process": {"type": "push", "duration": 0.5},
    "timeline": {"type": "wipe", "duration": 0.5},
    "infographic": {"type": "zoom-in", "duration": 0.45},
    "stats": {"type": "cover", "duration": 0.5},
    "comparison": {"type": "slide-left", "duration": 0.45},
    "summary": {"type": "dissolve", "duration": 0.55},
    "content": {"type": "fade", "duration": 0.45},
}

LAYOUT_BY_TYPE = {
    "hero": ["split", "left-right"],
    "process": ["zigzag", "grid"],
    "timeline": ["left-right", "split"],
    "infographic": ["circular", "grid"],
    "stats": ["split", "grid"],
    "comparison": ["split", "left-right"],
    "summary": ["split", "center"],
    "content": ["split", "left-right", "grid"],
}

VISUAL_HINTS = {
    "hero": "cinematic hero background with depth and lighting",
    "process": "workflow, team operations, clean process illustration",
    "timeline": "timeline roadmap concept with milestones",
    "infographic": "data infographic style visual with clean icons",
    "stats": "business analytics dashboard visualization",
    "comparison": "side by side concept imagery with contrast",
    "summary": "inspiring closing visual with subtle depth",
    "content": "professional contextual visual matching slide topic",
}


def _clamp_text(text: Any, max_chars: int) -> str:
    t = str(text or "").strip()
    if len(t) <= max_chars:
        return t
    trimmed = t[: max_chars + 1]
    cut = trimmed.rfind(" ")
    if cut > 0:
        return trimmed[:cut].rstrip()
    return trimmed[:max_chars].rstrip()


def _clean_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for v in values:
        s = str(v or "").strip()
        if s:
            out.append(s)
    return out


def _keyword_slice(text: str, fallback: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", (text or "").strip())
    if not words:
        return fallback
    return " ".join(words[:8])


def _topic_from_prompt(prompt: str, fallback: str = "presentation topic") -> str:
    p = str(prompt or "").strip()
    if not p:
        return fallback
    cleaned = re.sub(r"\s+", " ", p).strip()
    cleaned = re.sub(
        r"(?i)^\s*(create|generate|make|build|prepare|design)\s+(a\s+)?(ppt|presentation|deck|template)\s*(for|on|about|of|regarding)?\s*",
        "",
        cleaned,
    ).strip(" -:.,")
    cleaned = re.sub(r"(?i)\b(with|using)\s+\d+\s+slides?\b", "", cleaned).strip(" -:.,")
    return _keyword_slice(cleaned or p, fallback)


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _looks_like_prompt_echo(text: str, prompt: str) -> bool:
    t = _normalize_for_match(text)
    p = _normalize_for_match(prompt)
    if not t or not p:
        return False
    if len(t) < 10:
        return False
    if t in p or p in t:
        return True
    t_words = [w for w in t.split() if len(w) > 2]
    p_words = [w for w in p.split() if len(w) > 2]
    if not t_words or not p_words:
        return False
    overlap = len(set(t_words) & set(p_words))
    ratio = overlap / max(1, len(set(t_words)))
    return ratio >= 0.75


def _infer_type(idx: int, total: int, slide: dict) -> str:
    existing = str(slide.get("slide_type") or "").strip().lower()
    if existing:
        return existing
    content = slide.get("content") if isinstance(slide.get("content"), dict) else {}
    stats = content.get("stats") if isinstance(content, dict) else []
    steps = content.get("steps") if isinstance(content, dict) else []
    points = content.get("bullet_points") if isinstance(content, dict) else []
    if idx == 0:
        return "hero"
    if idx == total - 1:
        return "summary"
    if isinstance(stats, list) and len(stats) >= 2:
        return "stats"
    if isinstance(steps, list) and len(steps) >= 3:
        return "process"
    if isinstance(points, list) and len(points) >= 6:
        return "comparison"
    return "content"


def _pick_layout(slide_type: str, idx: int, heading: str) -> str:
    choices = LAYOUT_BY_TYPE.get(slide_type, LAYOUT_BY_TYPE["content"])
    if not choices:
        return "split"
    seed = abs(hash(f"{idx}:{heading}:{slide_type}"))
    return choices[seed % len(choices)]


def _density_for_slide(slide_type: str, bullet_count: int, stats_count: int) -> str:
    if slide_type in {"hero", "summary"}:
        return "minimal"
    if slide_type in {"stats", "comparison"} or bullet_count >= 6 or stats_count >= 3:
        return "detailed"
    return "balanced"


def _target_limits(density: str) -> tuple[int, int]:
    if density == "minimal":
        return (4, 64)
    if density == "detailed":
        return (6, 72)
    return (5, 68)


def _ensure_stats(raw_stats: Any) -> list[dict]:
    stats_list = raw_stats if isinstance(raw_stats, list) else []
    out: list[dict] = []
    for s in stats_list[:4]:
        if isinstance(s, dict):
            out.append(
                {
                    "label": _clamp_text(s.get("label"), 26),
                    "value": _clamp_text(s.get("value"), 18),
                    "unit": _clamp_text(s.get("unit"), 8),
                    "note": _clamp_text(s.get("note"), 24),
                }
            )
    return out


def _bounded_slide_count(value: Any, default: int = 6) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(1, min(30, n))


def _make_fallback_slide(idx: int, total: int, prompt: str) -> dict:
    topic = _topic_from_prompt(prompt, "Key topic")
    is_last = idx == total - 1
    title = "Summary" if is_last else f"Section {idx + 1}"
    heading = f"{topic} - {title}"
    points = (
        ["Key takeaway", "Recommended next action", "Expected impact"]
        if is_last
        else ["Core idea", "Supporting detail", "Practical example"]
    )
    slide_type = "summary" if is_last else "content"
    return {
        "title": title,
        "slide_type": slide_type,
        "layout": "split",
        "content_density": "balanced",
        "text_placement_zone": "left",
        "transition": TRANSITION_BY_TYPE.get(slide_type, TRANSITION_BY_TYPE["content"]),
        "background_image_query": "",
        "overlay_opacity": 0.0,
        "design_notes": "Fallback slide added to preserve exact requested slide count.",
        "content": {
            "heading": heading,
            "subheading": f"{topic} overview",
            "bullet_points": points,
            "steps": [],
            "stats": [],
        },
        "visual_elements": {
            "image_query": f"{topic}, {VISUAL_HINTS.get(slide_type, VISUAL_HINTS['content'])}",
            "icon_query": ["idea"],
            "shape_type": ["circle", "hexagon"],
        },
    }


def _fallback_subheading(slide_type: str, heading: str, topic_hint: str) -> str:
    core = _keyword_slice(heading, topic_hint)
    if slide_type == "process":
        return f"Practical steps to apply {core}"
    if slide_type == "timeline":
        return f"Milestones for improving {core}"
    if slide_type in {"stats", "comparison"}:
        return f"Key indicators for {core}"
    if slide_type == "summary":
        return f"Main takeaways for {core}"
    return f"Core insights on {core}"


def _fallback_points(slide_type: str, heading: str, topic_hint: str) -> list[str]:
    core = _keyword_slice(heading, topic_hint)
    if slide_type in {"process", "timeline"}:
        return [
            f"Set a clear goal for {core}",
            "Choose one habit to improve this week",
            "Review progress and refine your plan",
        ]
    if slide_type in {"stats", "comparison"}:
        return [
            f"Measure baseline for {core}",
            "Track changes over the next 4 weeks",
            "Compare outcomes and adjust strategy",
        ]
    if slide_type == "summary":
        return [
            f"Focus on the most impactful {core} habits",
            "Keep actions simple and consistent",
            "Use weekly reflection to sustain progress",
        ]
    return [
        f"Understand the fundamentals of {core}",
        "Apply practical actions in daily routine",
        "Monitor results and improve continuously",
    ]


def _fallback_steps(heading: str, topic_hint: str) -> list[str]:
    core = _keyword_slice(heading, topic_hint)
    return [
        f"Assess current {core} habits",
        "Create a realistic weekly plan",
        "Practice consistently each day",
        "Review and improve at week end",
    ]


def _fallback_stats(heading: str, topic_hint: str, points: list[str]) -> list[dict]:
    labels = points[:3] if points else [
        f"{_keyword_slice(heading, topic_hint)} adherence",
        "Weekly consistency",
        "Positive outcome rate",
    ]
    out = []
    for i, label in enumerate(labels[:3]):
        out.append({
            "label": _clamp_text(label, 26),
            "value": str(55 + i * 15),
            "unit": "%",
            "note": "sample baseline",
        })
    return out


def _ensure_slide_content(
    slide_type: str,
    heading: str,
    subheading: str,
    points: list[str],
    steps: list[str],
    stats: list[dict],
    topic_hint: str,
) -> tuple[str, list[str], list[str], list[dict]]:
    # Reuse available structured data before generating fallbacks.
    if not points and steps:
        points = [_clamp_text(s, 68) for s in steps[:4]]
    if not points and stats:
        points = [_clamp_text(str(s.get("label") or "Key metric"), 68) for s in stats[:4] if isinstance(s, dict)]

    if not points and not steps and not stats:
        points = _fallback_points(slide_type, heading, topic_hint)

    if slide_type in {"process", "timeline"} and len(steps) < 3:
        steps = _fallback_steps(heading, topic_hint)

    if slide_type in {"stats", "comparison"} and len(stats) < 2:
        stats = _fallback_stats(heading, topic_hint, points)

    if not subheading:
        subheading = _fallback_subheading(slide_type, heading, topic_hint)

    return subheading, points, steps, stats


def apply_auto_design(
    ai_content: dict,
    prompt: str,
    num_slides: int,
    slide_width: int,
    slide_height: int,
    is_template: bool = False,
) -> dict:
    content = ai_content if isinstance(ai_content, dict) else {}
    slides = content.get("slides")
    if not isinstance(slides, list):
        slides = []

    # Enforce exact requested slide count; some LLM responses can under/over-shoot.
    requested = _bounded_slide_count(num_slides, default=6)
    if len(slides) > requested:
        slides = slides[:requested]
    elif len(slides) < requested:
        for idx in range(len(slides), requested):
            slides.append(_make_fallback_slide(idx, requested, prompt))

    total = len(slides) if slides else requested

    safe_w = max(200, (slide_width or 960) - 120)
    safe_h = max(120, (slide_height or 540) - 120)
    topic_hint = _topic_from_prompt(prompt, "presentation topic")

    normalized_slides: list[dict] = []
    for idx, raw in enumerate(slides[:total]):
        slide = raw if isinstance(raw, dict) else {}
        content_block = slide.get("content") if isinstance(slide.get("content"), dict) else {}
        heading = _clamp_text(content_block.get("heading") or slide.get("heading") or slide.get("title") or f"Slide {idx + 1}", 52)
        subheading = _clamp_text(content_block.get("subheading") or slide.get("description") or "", 110)
        points = _clean_list(content_block.get("bullet_points") or slide.get("points"))
        steps = _clean_list(content_block.get("steps"))
        stats = _ensure_stats(content_block.get("stats"))

        slide_type = _infer_type(idx, total, slide)
        if _looks_like_prompt_echo(heading, prompt):
            if idx == total - 1 or slide_type == "summary":
                heading = "Key Takeaways"
            elif idx == 0 or slide_type == "hero":
                heading = f"{_keyword_slice(topic_hint, 'Topic').title()} Overview"
            else:
                heading = _clamp_text(f"{_keyword_slice(topic_hint, 'Topic').title()} Insights", 52)
        if _looks_like_prompt_echo(subheading, prompt):
            subheading = ""
        subheading, points, steps, stats = _ensure_slide_content(
            slide_type, heading, subheading, points, steps, stats, topic_hint
        )
        density = _density_for_slide(slide_type, len(points), len(stats))
        max_points, max_point_len = _target_limits(density)
        points = [_clamp_text(p, max_point_len) for p in points[:max_points]]
        steps = [_clamp_text(s, 60) for s in steps[:5]]
        stats = stats[:4]

        layout = _pick_layout(slide_type, idx, heading)
        text_zone = str(slide.get("text_placement_zone") or "").strip().lower()
        if text_zone not in {"left", "right", "center", "bottom"}:
            text_zone = "left" if layout in {"split", "left-right"} else "center"

        visual = slide.get("visual_elements") if isinstance(slide.get("visual_elements"), dict) else {}
        image_query = _clamp_text(
            slide.get("image_query") or visual.get("image_query") or f"{topic_hint}, {VISUAL_HINTS.get(slide_type, VISUAL_HINTS['content'])}",
            140,
        )
        icon_query = _clean_list(
            slide.get("icon_query")
            or slide.get("icon_queries")
            or visual.get("icon_query")
            or visual.get("icon_queries")
        )[:2]
        if not icon_query:
            icon_query = [_keyword_slice(heading, "idea")]

        bg_query = str(slide.get("background_image_query") or "").strip()
        if not bg_query and slide_type in {"hero", "summary"}:
            bg_query = _clamp_text(f"{topic_hint}, {VISUAL_HINTS.get(slide_type)}", 140)
        if slide_type in {"stats", "comparison"} and density == "detailed":
            bg_query = ""

        if bg_query:
            overlay = float(slide.get("overlay_opacity") or 0.0)
            overlay_opacity = min(max(overlay or 0.45, 0.35), 0.7)
        else:
            overlay_opacity = 0.0

        transition = slide.get("transition")
        if not isinstance(transition, dict):
            transition = TRANSITION_BY_TYPE.get(slide_type, TRANSITION_BY_TYPE["content"])

        normalized_slides.append(
            {
                **slide,
                "slide_type": slide_type,
                "layout": layout,
                "content_density": density,
                "text_placement_zone": text_zone,
                "title": _clamp_text(
                    ("Summary" if slide_type == "summary" else (slide.get("title") or heading))
                    if not _looks_like_prompt_echo(str(slide.get("title") or ""), prompt)
                    else ("Summary" if slide_type == "summary" else "Key Insights"),
                    38
                ),
                "heading": heading,
                "description": subheading,
                "points": points,
                "image_query": image_query,
                "background_image_query": bg_query,
                "overlay_opacity": overlay_opacity,
                "transition": transition,
                "content": {
                    "heading": heading,
                    "subheading": subheading,
                    "bullet_points": points,
                    "steps": steps,
                    "stats": stats,
                },
                "visual_elements": {
                    "image_query": image_query,
                    "icon_query": icon_query,
                    "shape_type": _clean_list(visual.get("shape_type"))[:2] or ["circle", "hexagon"],
                },
                "design_notes": _clamp_text(
                    slide.get("design_notes")
                    or f"Auto-designed with safe area {safe_w}x{safe_h}px, strong visual hierarchy, balanced spacing, and no overlap.",
                    200,
                ),
            }
        )

    content["slides"] = normalized_slides
    if not isinstance(content.get("theme"), (dict, str)):
        content["theme"] = {"name": "ocean-ink"}

    # Keep metadata for client-side layout intelligence.
    content["canvas"] = {"width": int(slide_width or 960), "height": int(slide_height or 540), "safe_margin": 60}
    content["auto_design"] = {"version": "v1", "template_mode": bool(is_template)}
    return content
