"""
Unified LLM service using LiteLLM for OpenAI models.
Returns structured JSON slide content + token usage metadata.

Features:
- Context-aware prompt analysis (kids, professional, academic, creative)
- Randomized design seeds for visual diversity
- Strict slide count enforcement
- Modern design pattern references (Bento Grid, Editorial, Glassmorphism)
- Feedback-rules integration for continuous improvement
"""

import json
import re
import time
import random
import logging
from typing import Awaitable, Callable, Any
import litellm
from config import DEFAULT_OPENAI_API_KEY, DEFAULT_OPENAI_MODEL

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True

# ─── Pricing table (per 1M tokens) ─────────────────────────
MODEL_PRICING = {
    "gpt-3.5-turbo":    {"input": 0.50,  "output": 1.50},
    "gpt-4":            {"input": 30.00, "output": 60.00},
    "gpt-4-32k":        {"input": 60.00, "output": 120.00},
    "gpt-4o":           {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":      {"input": 0.15,  "output": 0.60},
    "gpt-4.1":          {"input": 2.00,  "output": 8.00},
    "gpt-4.1-mini":     {"input": 0.40,  "output": 1.60},
    "gpt-4.1-nano":     {"input": 0.10,  "output": 0.40},
    "gpt-5-nano":       {"input": 0.10,  "output": 0.40},
    "gpt-5-mini":       {"input": 0.40,  "output": 1.60},
    "gpt-5.4":          {"input": 2.50,  "output": 15.00},
    "gpt-5.4-pro":      {"input": 5.00,  "output": 20.00},
    "gpt-5.4-mini":     {"input": 0.40,  "output": 1.60},
    "gpt-5.4-nano":     {"input": 0.10,  "output": 0.40},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate USD cost from token counts using the pricing table."""
    clean = model.replace("openai/", "").strip()
    pricing = MODEL_PRICING.get(clean)
    if not pricing:
        return 0.0
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


def _normalize_model(model: str) -> str:
    value = (model or "").strip()
    if not value:
        return DEFAULT_OPENAI_MODEL
    if value.startswith("openai/"):
        return value
    if any(value.startswith(prefix) for prefix in ("gpt-", "o1", "o3")):
        return f"openai/{value}"
    return DEFAULT_OPENAI_MODEL


def _resolve_model_and_key(model: str, openai_key: str = "") -> tuple[str, str]:
    """Resolve the litellm model string and API key based on the selected model."""
    model = _normalize_model(model)
    key = (openai_key or DEFAULT_OPENAI_API_KEY).strip()
    if not key:
        raise ValueError("OpenAI API key not configured. Please set it in Settings.")
    return model, key


def _parse_json_response(content: str) -> dict:
    """Parse LLM response content as JSON, with fallback extraction."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError("Failed to parse AI response as JSON")


def _extract_usage(response, model: str) -> dict:
    """Extract token usage and calculate cost from a litellm response."""
    usage = getattr(response, "usage", None)
    if not usage:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "model": model, "cost_usd": 0.0}
    pt = getattr(usage, "prompt_tokens", 0) or 0
    ct = getattr(usage, "completion_tokens", 0) or 0
    tt = getattr(usage, "total_tokens", 0) or (pt + ct)
    return {
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": tt,
        "model": model,
        "cost_usd": calculate_cost(model, pt, ct),
    }


def _merge_usage(base: dict, extra: dict) -> dict:
    b = base or {}
    e = extra or {}
    pt = int(b.get("prompt_tokens", 0) or 0) + int(e.get("prompt_tokens", 0) or 0)
    ct = int(b.get("completion_tokens", 0) or 0) + int(e.get("completion_tokens", 0) or 0)
    tt = int(b.get("total_tokens", 0) or 0) + int(e.get("total_tokens", 0) or (int(e.get("prompt_tokens", 0) or 0) + int(e.get("completion_tokens", 0) or 0)))
    model = e.get("model") or b.get("model") or ""
    return {
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": tt,
        "model": model,
        "cost_usd": calculate_cost(model, pt, ct) if model else 0.0,
    }


class _SlidesArrayParser:
    """
    Incrementally parses slide objects from a streaming JSON response.
    It scans for the `slides` array and emits each complete `{...}` object inside it.
    """

    def __init__(self):
        self.buffer = ""
        self.pos = 0
        self.in_string = False
        self.escape = False
        self.in_slides = False
        self.brace_depth = 0
        self.obj_start = -1
        self.slides_started = False

    def feed(self, chunk: str) -> list[dict]:
        if not chunk:
            return []
        self.buffer += chunk
        out: list[dict] = []

        while self.pos < len(self.buffer):
            c = self.buffer[self.pos]

            if not self.in_slides:
                if not self.slides_started:
                    marker = self.buffer.find('"slides"', self.pos)
                    if marker == -1:
                        self.pos = max(0, len(self.buffer) - 32)
                        break
                    self.pos = marker + len('"slides"')
                    self.slides_started = True
                    continue

                if c == "[":
                    self.in_slides = True
                self.pos += 1
                continue

            # In slides array
            if self.in_string:
                if self.escape:
                    self.escape = False
                elif c == "\\":
                    self.escape = True
                elif c == '"':
                    self.in_string = False
                self.pos += 1
                continue

            if c == '"':
                self.in_string = True
                self.pos += 1
                continue

            if c == "{":
                if self.brace_depth == 0:
                    self.obj_start = self.pos
                self.brace_depth += 1
                self.pos += 1
                continue

            if c == "}":
                if self.brace_depth > 0:
                    self.brace_depth -= 1
                    if self.brace_depth == 0 and self.obj_start >= 0:
                        raw_obj = self.buffer[self.obj_start:self.pos + 1]
                        try:
                            parsed = json.loads(raw_obj)
                            if isinstance(parsed, dict):
                                out.append(parsed)
                        except Exception:
                            pass
                        self.obj_start = -1
                self.pos += 1
                continue

            if c == "]" and self.brace_depth == 0:
                self.pos += 1
                # No need to parse beyond slides for incremental extraction.
                break

            self.pos += 1

        return out


# ─── CONTEXT ANALYSIS ─────────────────────────────────────────

KIDS_KEYWORDS = [
    "kids", "children", "child", "kid", "kindergarten", "nursery",
    "primary", "lkg", "ukg", "playschool", "pre-school", "preschool",
    "class 1", "class 2", "class 3", "class 4", "class 5",
    "class i", "class ii", "class iii", "class iv", "class v",
    "grade 1", "grade 2", "grade 3", "grade 4", "grade 5",
    "1st grade", "2nd grade", "3rd grade", "4th grade", "5th grade",
    "below class 5", "below class 4", "below 5", "below 4",
    "toddler", "young learners", "elementary", "cartoon",
    "toys", "toy", "fun learning", "playful",
]

PROFESSIONAL_KEYWORDS = [
    "business", "corporate", "investor", "startup", "pitch deck",
    "strategy", "analytics", "finance", "quarterly", "revenue",
    "roi", "kpi", "stakeholder", "boardroom", "executive",
    "enterprise", "consulting", "market analysis", "competitive",
    "b2b", "saas", "product launch", "go-to-market",
]

ACADEMIC_KEYWORDS = [
    "university", "college", "thesis", "dissertation", "journal",
    "research paper", "academic", "lecture", "professor", "phd",
    "scientific", "methodology", "literature review", "peer review",
    "hypothesis", "abstract", "bibliography", "citation",
]

CREATIVE_KEYWORDS = [
    "story", "narrative", "portfolio", "creative", "art",
    "design", "fashion", "photography", "illustration", "brand",
    "cultural", "heritage", "travel", "lifestyle", "music",
    "film", "media", "entertainment", "event",
]


def _analyze_prompt_context(prompt: str) -> dict:
    """
    Analyze the user's prompt to detect audience and context.
    Returns a dict with context type and confidence signals.
    """
    text = prompt.lower().strip()

    # Score each category
    kids_score = sum(1 for kw in KIDS_KEYWORDS if kw in text)
    prof_score = sum(1 for kw in PROFESSIONAL_KEYWORDS if kw in text)
    acad_score = sum(1 for kw in ACADEMIC_KEYWORDS if kw in text)
    creative_score = sum(1 for kw in CREATIVE_KEYWORDS if kw in text)

    scores = {
        "kids": kids_score,
        "professional": prof_score,
        "academic": acad_score,
        "creative": creative_score,
    }

    # Determine primary context
    max_score = max(scores.values())
    if max_score == 0:
        context_type = "general"
    else:
        context_type = max(scores, key=scores.get)

    return {
        "type": context_type,
        "scores": scores,
        "is_kids": kids_score >= 1,
        "is_professional": prof_score >= 1,
        "is_academic": acad_score >= 1,
        "is_creative": creative_score >= 1,
    }


# ─── DESIGN PATTERN LIBRARY ──────────────────────────────────
# Modern PPT design patterns referenced from 2025/2026 trends

DESIGN_PATTERNS = [
    "Bento Grid — modular card-based layout with distinct content zones, inspired by Apple's design. Each card has rounded corners, subtle shadows, and clear visual hierarchy.",
    "Editorial Magazine — asymmetric grids with generous whitespace, pull quotes in large serif fonts, hero images spanning 60% of the slide, and disciplined two-column text flow.",
    "Glassmorphism — frosted-glass panels over gradient backgrounds with subtle blur, light borders, and depth-through-transparency. Premium, modern feel.",
    "Bold Typographic — oversized sans-serif headlines (60-80pt equivalent), minimal imagery, color-blocked backgrounds. The typography IS the visual element.",
    "Data Storytelling — clean charts with annotations, single-insight callouts, muted gridlines, accent-colored data points. Each chart tells one clear story.",
    "Split Canvas — slide divided into two distinct halves (image + text, or dark + light), creating visual tension and clear information zones.",
    "Gradient Flow — smooth gradient backgrounds transitioning between theme colors, with floating text cards and subtle shadow depth.",
    "Minimal Zen — extreme whitespace, single focal element per slide, thin-line icons, muted color palette with one bold accent. Breathable and elegant.",
    "Layered Depth — overlapping elements with shadows creating z-axis depth, background shapes peeking behind content cards, parallax-inspired composition.",
    "Infographic Narrative — connected visual elements telling a sequential story, using arrows, numbered nodes, and progressive reveal layouts.",
]


def _generate_design_seed() -> str:
    """Generate a unique design seed to force variety in each generation."""
    patterns = random.sample(DESIGN_PATTERNS, min(3, len(DESIGN_PATTERNS)))
    seed_id = f"DS-{int(time.time()) % 100000}-{random.randint(100, 999)}"
    return seed_id, patterns


def _build_context_directives(context: dict) -> str:
    """Build context-specific design directives based on prompt analysis."""

    if context["type"] == "kids":
        return """
## 🎨 KID-FRIENDLY DESIGN MODE (ACTIVATED)
This presentation is for YOUNG CHILDREN (primary school / kindergarten level). Apply these rules STRICTLY:

### Visual Style
- Use BRIGHT, VIBRANT, RAINBOW colors. Think: sunshine yellow (#FFD93D), sky blue (#6BCB77), candy pink (#FF6B9D), grass green (#4ECDC4), orange (#FF8C42)
- Mode MUST be "light" — white or very light pastel backgrounds
- Include playful visual elements: rounded shapes, stars, clouds, rainbows, hearts
- Image queries MUST include terms like: "cartoon illustration", "cute character", "colorful kids", "playful animated"
- Use decorative shapes: circle, star, cloud, heart — NOT corporate hexagons or diamonds

### Typography & Content
- Headings: SHORT (≤4 words), FUN, use exclamation marks! Question marks?
- Body text: VERY SIMPLE language, ≤40 characters per bullet point
- Maximum 3 bullet points per slide
- Use playful fonts: "Sora" for headings (most playful in allowed list), "DM Sans" for body
- Stats should use kid-friendly numbers and fun units (e.g., "🌟 5 stars!", "🎈 10 balloons")

### Layout
- Use "split" layout with large images (70% of slide) and minimal text
- Content density: ALWAYS "minimal"
- Generous spacing — never crowd elements
- Every slide MUST have a colorful, engaging image

### Theme
- palette.background: light pastel (#FFF8E7, #E8F8F5, #FDE8F0, #E8F0FE)
- palette.primary: bright saturated color
- palette.accent: contrasting bright color
- style_notes: "Playful, colorful, cartoon-inspired children's presentation with rounded elements and joyful imagery"
"""

    elif context["type"] == "professional":
        return """
## 📊 PROFESSIONAL / BUSINESS MODE (ACTIVATED)
This is a high-stakes business presentation. Apply premium design standards:

### Visual Style
- Use sophisticated, muted color palettes: deep navy (#1B2A4A), slate (#2D3748), charcoal (#1A202C) with strategic accent colors
- Mode should be "dark" for impact, or "light" with muted backgrounds for readability
- Image queries: "professional business", "modern office", "data analytics", "corporate team", "abstract geometric"
- Use geometric shapes: hexagon, diamond, rectangle — conveying structure and precision

### Typography & Content
- Headings: Authority-driven, data-informed (e.g., "42% Revenue Growth in Q3")
- Include DATA on every applicable slide: stats, percentages, growth figures, comparisons
- Bullet points: insight-driven, each starting with an action verb or metric
- Use "Space Grotesk" or "Inter" for headings, "Inter" for body
- Include comparison slides, stats slides, and process slides

### Layout
- Use "Bento Grid" and "Split Canvas" patterns for data-heavy slides
- Mix "grid" and "split" layouts — never repeat the same layout consecutively
- Content density: "balanced" to "detailed" — maximize information per slide
- Include background_image_query ONLY for hero/summary slides

### Data Visualization
- Stats slides MUST have numeric values with units and context notes
- Include at least 2 stats/comparison slides per deck
- Steps should represent actionable business processes
- Use chart-ready data formats

### Theme
- fonts.heading: "Space Grotesk" (modern, authoritative)
- style_notes: "Premium corporate design with data-driven layouts, sophisticated palette, and executive-level polish"
"""

    elif context["type"] == "academic":
        return """
## 🎓 ACADEMIC / RESEARCH MODE (ACTIVATED)
This is an academic/research presentation. Apply scholarly design standards:

### Visual Style
- Clean, structured layouts with generous whitespace
- Muted, professional colors: navy, forest green, burgundy with cream/white backgrounds
- Image queries: "research illustration", "scientific diagram", "academic concept", "data visualization"
- Use structured shapes: rectangles for data containers, circles for concepts, arrows for flow

### Typography & Content
- Headings: Clear, descriptive, thesis-statement style
- Content: Evidence-based, structured arguments with supporting data
- Use numbered lists for methodology steps
- Include citation-style references where appropriate
- Subheadings should provide context and framework
- Use "Manrope" or "Inter" for clean readability

### Layout
- Use "Editorial Magazine" pattern with clear information hierarchy
- Process slides for methodology, timeline for research phases
- Grid layouts for literature review or comparative analysis
- Content density: "detailed" for evidence slides, "balanced" for overview

### Theme
- Mode: "light" (academic papers are traditionally light)
- Clean, high-contrast palette with minimal decorative elements
- style_notes: "Scholarly, clean, evidence-driven presentation with clear information hierarchy and structured argumentation"
"""

    elif context["type"] == "creative":
        return """
## 🎨 CREATIVE / STORYTELLING MODE (ACTIVATED)
This is a creative/narrative presentation. Apply artistic design standards:

### Visual Style
- Bold, expressive color palettes — don't be safe, be memorable
- Rich imagery with emotional impact
- Use artistic shapes and decorative elements
- Image queries: "artistic", "cinematic", "dramatic lighting", "creative composition", "visual storytelling"

### Typography & Content
- Headings: Evocative, emotional, story-driven
- Use narrative arc: setup → conflict → resolution → takeaway
- Minimal bullet points — prefer single impactful statements
- Use "Playfair Display" for elegant headings, "DM Sans" for body
- Let images carry the story; text should complement, not dominate

### Layout
- Full-bleed images with text overlays for maximum visual impact
- "Gradient Flow" and "Layered Depth" design patterns
- Content density: "minimal" — every word must earn its place
- Generous use of background images with overlay_opacity 0.5-0.7

### Theme
- Bold gradients, rich textures, cinematic feel
- style_notes: "Cinematic, emotionally resonant creative presentation with bold imagery and narrative-driven flow"
"""

    else:
        return """
## 🌟 GENERAL PRESENTATION MODE
Create a polished, modern presentation following current design best practices:

### Design Approach
- Follow the "one idea per slide" principle
- Use modern layout patterns: Bento Grid, Split Canvas, or Editorial Magazine
- Ensure strong visual hierarchy with clear focal points
- Balance text and imagery — neither should overwhelm

### Visual Quality
- Image queries must be SPECIFIC and DESCRIPTIVE (not generic)
- Use geometric accent shapes for visual interest
- Apply subtle depth through layering and shadows
- Choose colors that match the topic's emotional tone

### Content Quality
- Headings: impactful, memorable, concise
- Bullet points: insight-driven, not just informational
- Include data/statistics where they add credibility
- Follow a narrative arc from introduction to conclusion
"""


# ─── PROFESSIONAL SYSTEM PROMPT ───────────────────────────────

def _build_ppt_system_prompt(
    num_slides: int,
    slide_width: int,
    slide_height: int,
    context: dict | None = None,
    design_seed: str = "",
    design_patterns: list | None = None,
    feedback_rules: str = "",
) -> str:
    context = context or {"type": "general"}
    context_directives = _build_context_directives(context)
    design_patterns = design_patterns or []
    pattern_str = "\n".join(f"  - {p}" for p in design_patterns) if design_patterns else "  - Use varied, modern layout patterns"

    feedback_section = ""
    if feedback_rules and feedback_rules.strip():
        feedback_section = f"""

## ⚡ USER FEEDBACK IMPROVEMENTS (APPLY THESE)
Previous generations received feedback. Apply these learned improvements:
{feedback_rules}
"""

    return f"""You are an **elite presentation designer** with 15+ years of experience creating award-winning slides for Fortune 500 companies, TED talks, and high-stakes pitches.

Your task: Generate a structured JSON presentation that is **visually stunning, narratively compelling, and professionally balanced**.

## CRITICAL: SLIDE COUNT
You MUST generate EXACTLY **{num_slides}** slides — no more, no fewer. This is non-negotiable. Count your slides carefully before outputting.

## CANVAS CONSTRAINTS
- Slide dimensions: **{slide_width}px × {slide_height}px**
- Safe margins: **60px** on all sides (text and images must stay within {slide_width - 120}px × {slide_height - 120}px usable area)
- Plan all text lengths so they FIT within these bounds. Short, impactful text ALWAYS.

## DESIGN SEED: {design_seed}
This is a unique generation. You MUST create a FRESH, UNIQUE design that differs from any previous generation.
Prioritize these design patterns for THIS generation:
{pattern_str}

{context_directives}
{feedback_section}

## OUTPUT FORMAT
Return ONLY valid JSON (no markdown, no code fences, no commentary):
{{
  "title": "Presentation Title",
  "theme": {{
    "name": "unique-theme-name-{design_seed}",
    "mode": "dark" or "light",
    "palette": {{
      "background": "#hex",
      "surface": "#hex",
      "primary": "#hex",
      "secondary": "#hex",
      "accent": "#hex",
      "text": "#hex",
      "muted": "#hex"
    }},
    "fonts": {{
      "heading": "Font Name",
      "body": "Font Name"
    }},
    "style_notes": "Brief aesthetic description including which design pattern you're using"
  }},
  "slides": [
    {{
      "title": "Short label (≤6 words)",
      "slide_type": "hero|process|timeline|infographic|stats|comparison|content|summary",
      "layout": "split|left-right|grid|zigzag|circular",
      "content_density": "minimal|balanced|detailed",
      "text_placement_zone": "left|right|center|bottom",
      "transition": {{"type": "fade|slide-left|slide-right|zoom-in|push|wipe|cover|dissolve", "duration": 0.3 to 1.2}},
      "background_image_query": "specific descriptive query OR empty string",
      "overlay_opacity": 0.0 to 0.7,
      "design_notes": "Brief layout intent for the renderer — mention which design pattern used",
      "content": {{
        "heading": "Powerful heading (≤50 chars)",
        "subheading": "Supporting context (≤100 chars)",
        "bullet_points": ["Concise point ≤70 chars", ...],
        "steps": ["Action step ≤60 chars", ...],
        "stats": [{{"label": "Metric", "value": "42", "unit": "%", "note": "YoY"}}]
      }},
      "visual_elements": {{
        "image_query": "Specific, descriptive image search query",
        "icon_query": ["keyword1", "keyword2"],
        "shape_type": ["circle", "hexagon"]
      }}
    }}
  ]
}}

## DESIGN RULES (MANDATORY)

### Text Limits — NO EXCEPTIONS
- Headings: **≤50 characters**. Be punchy and memorable.
- Subheadings: **≤100 characters**. Add real value, never repeat the heading.
- Bullet points: **3–5 per slide**, each **≤70 characters**. Think billboard copywriting.
- Steps: **3–5 per slide**, each **≤60 characters**. Start with action verbs.
- Stats: **2–4 per slide** with numeric values and clear units.
- For stats slides, provide numeric `value` fields so chart rendering is possible.

### Visual Balance — ALWAYS
- Every slide MUST have visual elements (images, icons, or decorative shapes).
- `image_query` must be **specific and descriptive** (e.g., "team collaborating in modern glass office with natural light" NOT "business").
- Icon queries: 1–2 simple keywords per icon.
- Shape types: Use to support infographic layouts (circle, hexagon, arrow, diamond).

### DESIGN PATTERN DIVERSITY (CRITICAL)
- You MUST vary your design approach across slides. NEVER use the same layout pattern for consecutive slides.
- Each slide should feel visually distinct while maintaining theme cohesion.
- Alternate between text-heavy and visual-heavy slides.
- Use at least 3 different layout patterns across the deck.
- Design notes should reference specific modern design patterns (Bento Grid, Editorial, Split Canvas, etc.)

### Background Images — INTELLIGENT USE
- `background_image_query`: Provide ONLY when a background image would **genuinely enhance** the visual impact.
- Use for: hero slides, atmospheric/mood slides, full-bleed visual slides.
- Do NOT use for: data-heavy slides, text-dense slides, or when theme colors provide enough interest.
- When set, ALWAYS pair with `overlay_opacity` (0.4–0.7) so text remains readable.
- When NOT needed, set `background_image_query` to empty string `""` and `overlay_opacity` to `0.0`.

### Layout Intelligence
- `text_placement_zone`: Where the primary text should anchor. Use "left" for split layouts with right-side images, "center" for hero/title slides, "right" for left-side visual layouts.
- `content_density`: "minimal" = large fonts, few words (hero/title), "balanced" = standard, "detailed" = smaller fonts, more data.
- Vary layouts across the deck. NEVER repeat the same layout consecutively.
- Respect spacing discipline for a {slide_width}x{slide_height} canvas with safe margins.

### Spacing & Alignment (CRITICAL for professional quality)
- Maintain consistent vertical rhythm: heading at top, content in middle, footer elements at bottom
- Use a clear grid system: elements should align to invisible gridlines
- Minimum 40px gap between distinct content groups
- Text blocks should have consistent left alignment within their zone
- Images and shapes should snap to the grid, not float randomly

### Motion Guidance
- Provide `transition` per slide.
- Use subtle transitions for content-heavy slides (fade/push/wipe) and stronger transitions for hero or section-break slides.

### Storytelling Flow (EXACTLY {num_slides} SLIDES)
Slides MUST follow a narrative arc:
1. **Hero/Title** (slide 1) — bold opener, minimal text, strong visual
2. **Context/Problem** — set the stage
3. **Deep Content** (process, timeline, infographic) — the core message
4. **Evidence** (stats, comparison) — data backing
5. **Summary/CTA** (last slide) — clear takeaway or call to action

### Theme Design
- Generate a **unique custom theme** that perfectly matches the topic's emotion, tone, and domain.
- The theme name MUST include the design seed "{design_seed}" to ensure uniqueness.
- Color choices must be **harmonious** (use complementary or analogous palettes). NEVER use generic pure red/blue/green.
- ONLY use fonts from: "Space Grotesk", "Inter", "Manrope", "Sora", "DM Sans", "Playfair Display"

### Slide Type Requirements
Include diverse slide types. Suggested variety: hero → content → process → timeline → infographic → stats → comparison → summary
REMEMBER: Generate EXACTLY {num_slides} slides. Count them.
"""


def _build_template_system_prompt(
    num_slides: int,
    slide_width: int,
    slide_height: int,
    context: dict | None = None,
    design_seed: str = "",
    design_patterns: list | None = None,
    feedback_rules: str = "",
) -> str:
    base = _build_ppt_system_prompt(
        num_slides, slide_width, slide_height,
        context, design_seed, design_patterns, feedback_rules,
    )
    template_addon = """

### TEMPLATE-SPECIFIC RULES
- Include **placeholders** using double curly braces: {{StudentName}}, {{Class}}, {{Division}}, {{SchoolName}}, {{Date}}, {{Topic}}
- For school templates: cover slide with StudentName, Class, Division, SchoolName placeholders
- For early grades (LKG/UKG): use bright, playful colors and kid-friendly language
- For professional templates: clean, corporate aesthetics
- Placeholders count toward character limits — keep surrounding text short
- REMEMBER: Generate EXACTLY {num_slides} slides including placeholders.
"""
    return base + template_addon


def _chunk_to_text(chunk: Any) -> str:
    try:
        choices = getattr(chunk, "choices", None)
        if not choices and isinstance(chunk, dict):
            choices = chunk.get("choices")
        if not choices:
            return ""
        ch0 = choices[0]
        delta = getattr(ch0, "delta", None)
        if delta is None and isinstance(ch0, dict):
            delta = ch0.get("delta")
        if delta is None:
            return ""
        content = getattr(delta, "content", None)
        if content is None and isinstance(delta, dict):
            content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    txt = item.get("text") or item.get("content")
                    if isinstance(txt, str):
                        parts.append(txt)
            return "".join(parts)
        return ""
    except Exception:
        return ""


async def _generate_content_streaming(
    *,
    litellm_model: str,
    api_key: str,
    system_prompt: str,
    user_message: str,
    on_partial_slide: Callable[[int, dict], Awaitable[None]] | None = None,
) -> tuple[dict, dict]:
    parser = _SlidesArrayParser()
    streamed_text = ""
    usage_from_stream: dict = {}
    slide_idx = 0

    stream = await litellm.acompletion(
        model=litellm_model,
        api_key=api_key,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.75,
        max_tokens=4096,
        response_format={"type": "json_object"},
        timeout=120.0,
        stream=True,
        stream_options={"include_usage": True},
    )

    async for chunk in stream:
        piece = _chunk_to_text(chunk)
        if piece:
            streamed_text += piece
            new_slides = parser.feed(piece)
            if on_partial_slide:
                for slide in new_slides:
                    await on_partial_slide(slide_idx, slide)
                    slide_idx += 1

        chunk_usage = getattr(chunk, "usage", None)
        if not chunk_usage and isinstance(chunk, dict):
            chunk_usage = chunk.get("usage")
        if chunk_usage:
            pt = getattr(chunk_usage, "prompt_tokens", None)
            ct = getattr(chunk_usage, "completion_tokens", None)
            tt = getattr(chunk_usage, "total_tokens", None)
            if isinstance(chunk_usage, dict):
                pt = chunk_usage.get("prompt_tokens", pt)
                ct = chunk_usage.get("completion_tokens", ct)
                tt = chunk_usage.get("total_tokens", tt)
            usage_from_stream = {
                "prompt_tokens": int(pt or 0),
                "completion_tokens": int(ct or 0),
                "total_tokens": int(tt or (int(pt or 0) + int(ct or 0))),
                "model": litellm_model,
                "cost_usd": calculate_cost(litellm_model, int(pt or 0), int(ct or 0)),
            }

    result = _parse_json_response(streamed_text)
    if "title" not in result or "slides" not in result:
        raise ValueError("AI response missing required fields")
    if not usage_from_stream:
        usage_from_stream = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model": litellm_model,
            "cost_usd": 0.0,
        }
    return result, usage_from_stream


async def generate_ppt_content(
    prompt: str,
    num_slides: int = 6,
    openai_key: str = "",
    model: str = DEFAULT_OPENAI_MODEL,
    slide_width: int = 960,
    slide_height: int = 540,
    feedback_rules: str = "",
    on_partial_slide: Callable[[int, dict], Awaitable[None]] | None = None,
) -> tuple[dict, dict]:
    """Generate structured PPT content. Returns (content_dict, usage_dict)."""
    litellm_model, api_key = _resolve_model_and_key(model, openai_key)
    logger.info(f"Generating PPT content with model: {litellm_model}")

    # Analyze prompt context
    context = _analyze_prompt_context(prompt)
    logger.info(f"Prompt context detected: {context['type']} (scores: {context['scores']})")

    # Generate design seed for variety
    design_seed, design_patterns = _generate_design_seed()

    system_prompt = _build_ppt_system_prompt(
        num_slides, slide_width, slide_height,
        context, design_seed, design_patterns, feedback_rules,
    )

    if on_partial_slide:
        try:
            result, usage = await _generate_content_streaming(
                litellm_model=litellm_model,
                api_key=api_key,
                system_prompt=system_prompt,
                user_message=f"Create a stunning presentation about: {prompt}",
                on_partial_slide=on_partial_slide,
            )
        except Exception as e:
            logger.warning(f"Streaming LLM path failed, falling back to non-stream mode: {e}")
            response = await litellm.acompletion(
                model=litellm_model,
                api_key=api_key,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Create a stunning presentation about: {prompt}"},
                ],
                temperature=0.75,
                max_tokens=4096,
                response_format={"type": "json_object"},
                timeout=120.0,
            )
            content = response.choices[0].message.content
            result = _parse_json_response(content)
            usage = _extract_usage(response, litellm_model)
    else:
        response = await litellm.acompletion(
            model=litellm_model,
            api_key=api_key,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a stunning presentation about: {prompt}"},
            ],
            temperature=0.75,  # Slightly higher for more creative variety
            max_tokens=4096,
            response_format={"type": "json_object"},
            timeout=120.0,
        )

        content = response.choices[0].message.content
        result = _parse_json_response(content)
        usage = _extract_usage(response, litellm_model)

    if "title" not in result or "slides" not in result:
        raise ValueError("AI response missing required fields")

    # Log slide count for debugging
    actual_slides = len(result.get("slides", []))
    if actual_slides != num_slides:
        logger.warning(f"LLM returned {actual_slides} slides but {num_slides} were requested")

    return result, usage


async def generate_template_content(
    prompt: str,
    num_slides: int = 6,
    openai_key: str = "",
    model: str = DEFAULT_OPENAI_MODEL,
    slide_width: int = 960,
    slide_height: int = 540,
    feedback_rules: str = "",
    on_partial_slide: Callable[[int, dict], Awaitable[None]] | None = None,
) -> tuple[dict, dict]:
    """Generate structured template content. Returns (content_dict, usage_dict)."""
    litellm_model, api_key = _resolve_model_and_key(model, openai_key)
    logger.info(f"Generating template content with model: {litellm_model}")

    # Analyze prompt context
    context = _analyze_prompt_context(prompt)
    logger.info(f"Template context detected: {context['type']} (scores: {context['scores']})")

    # Generate design seed for variety
    design_seed, design_patterns = _generate_design_seed()

    system_prompt = _build_template_system_prompt(
        num_slides, slide_width, slide_height,
        context, design_seed, design_patterns, feedback_rules,
    )

    if on_partial_slide:
        try:
            result, usage = await _generate_content_streaming(
                litellm_model=litellm_model,
                api_key=api_key,
                system_prompt=system_prompt,
                user_message=f"Create a presentation template about: {prompt}",
                on_partial_slide=on_partial_slide,
            )
        except Exception as e:
            logger.warning(f"Streaming template LLM path failed, falling back to non-stream mode: {e}")
            response = await litellm.acompletion(
                model=litellm_model,
                api_key=api_key,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Create a presentation template about: {prompt}"},
                ],
                temperature=0.75,
                max_tokens=4096,
                response_format={"type": "json_object"},
                timeout=120.0,
            )
            content = response.choices[0].message.content
            result = _parse_json_response(content)
            usage = _extract_usage(response, litellm_model)
    else:
        response = await litellm.acompletion(
            model=litellm_model,
            api_key=api_key,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a presentation template about: {prompt}"},
            ],
            temperature=0.75,
            max_tokens=4096,
            response_format={"type": "json_object"},
            timeout=120.0,
        )

        content = response.choices[0].message.content
        result = _parse_json_response(content)
        usage = _extract_usage(response, litellm_model)

    if "title" not in result or "slides" not in result:
        raise ValueError("AI response missing required fields")

    actual_slides = len(result.get("slides", []))
    if actual_slides != num_slides:
        logger.warning(f"Template LLM returned {actual_slides} slides but {num_slides} were requested")

    return result, usage
