import httpx
import json
import logging
from config import DEFAULT_GROQ_API_KEY

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def generate_ppt_content(prompt: str, num_slides: int = 6, api_key: str = "", slide_width: int = 960, slide_height: int = 540) -> dict:
    """Generate structured PPT content using Groq LLM API."""
    key = (api_key or DEFAULT_GROQ_API_KEY).strip()
    if not key:
        raise ValueError("Groq API key not configured. Please set it in Settings.")

    system_prompt = f"""You are a professional presentation designer and visual storyteller.
Generate a structured JSON presentation based on the user's request.

Create exactly {num_slides} slides. Return ONLY valid JSON (no markdown, no code blocks) in this exact format.
IMPORTANT: Slides are rendered on a canvas of **{slide_width}px width x {slide_height}px height**.
Safe margins: **60px** on all sides.
Use these constraints when planning layout, image placement, shapes, and text length. Intelligent padding, calculating sizes correctly for positioning is extremely important.
When using "split" or "left-right" layouts, assume a text column ~40% wide and an image/visual column ~40% wide, adjusted intelligently based on total width {slide_width}px.
{{
  "title": "Presentation Title",
  "theme": {{
    "name": "Custom Topic Theme",
    "mode": "dark",
    "palette": {{
      "background": "#0b0b1f",
      "surface": "#1b1b34",
      "primary": "#ff6b7a",
      "secondary": "#6c63ff",
      "accent": "#ffa94d",
      "text": "#f8f7ff",
      "muted": "#b4b2d1"
    }},
    "fonts": {{
      "heading": "Space Grotesk",
      "body": "Inter"
    }},
    "style_notes": "Short phrase characterizing the aesthetics"
  }},
  "slides": [
    {{
      "title": "Short slide title",
      "slide_type": "hero",
      "layout": "split",
      "content": {{
        "heading": "Slide Heading",
        "subheading": "Supporting subheading",
        "bullet_points": ["Point 1", "Point 2", "Point 3"],
        "steps": ["Step 1", "Step 2", "Step 3"],
        "stats": [{{ "label": "Metric", "value": "42", "unit": "%", "note": "YoY" }}]
      }},
      "visual_elements": {{
        "image_query": "Specific image search query",
        "icon_query": ["icon keyword", "second keyword"],
        "shape_type": ["circle", "hexagon", "arrow"]
      }}
    }}
  ]
}}

Rules:
- Make the content professional, engaging, and well-structured
- Slides must follow a logical storytelling sequence
- Must include these slide types at least once when {num_slides} >= 6:
  hero, process, timeline, infographic, stats, comparison
- Suggested order: hero → process → timeline → infographic → stats → comparison → (summary/CTA if extra slides)
- Use layout values only from: grid, zigzag, circular, left-right, split
- Each slide should have 4-6 bullet points where relevant
- Each bullet should be specific and 8-14 words long
- For process/timeline slides, fill "steps" with 4-6 items (short, action-oriented)
- For stats slides, provide 3-5 stats with numeric values and clear units
- Subheading should be 12-20 words and add meaning, not just repeat the heading
- Keep headings under 8 words where possible
- Keep all text short enough to fit inside the {slide_width}x{slide_height} layout and 60px margins
- Image queries should be specific and descriptive (e.g., "modern office team collaboration")
- Icons should be simple, minimal keywords (1-2 words)
- Shapes should support infographic-style design (circle, hexagon, arrow, line)
- CRITICAL: Generate a completely custom "theme" object filled with proper matching HEX color codes that completely perfectly matches the requested topic's emotion, tone, and environment. Never reuse identical themes.
- Choose ONLY from these safe fonts: "Space Grotesk", "Inter", "Manrope", "Sora", "DM Sans", "Playfair Display"
- IMPORTANT: Vary the layouts deliberately across the presentation. Never use the same layout successively unless necessary.
- Content MUST embrace proper storytelling: Introduction (hero), core concepts smoothly, detailed elaboration, and strong conclusive takeaway.
- First slide is a hero/title slide, last slide is summary/CTA if appropriate
- Content should be concise but informative
"""

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a presentation about: {prompt}"},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("Failed to parse AI response as JSON")

    # Validate structure
    if "title" not in result or "slides" not in result:
        raise ValueError("AI response missing required fields")

    return result


async def generate_template_content(prompt: str, num_slides: int = 6, api_key: str = "", slide_width: int = 960, slide_height: int = 540) -> dict:
    """Generate structured PPT template content using Groq LLM API."""
    key = (api_key or DEFAULT_GROQ_API_KEY).strip()
    if not key:
        raise ValueError("Groq API key not configured. Please set it in Settings.")

    system_prompt = f"""You are a professional presentation template designer. Generate a reusable TEMPLATE with placeholders.

Create exactly {num_slides} slides. Return ONLY valid JSON (no markdown, no code blocks) in this exact format.
IMPORTANT: Slides are rendered on a canvas of **{slide_width}px width x {slide_height}px height**.
Safe margins: **60px** on all sides.
Use these constraints when planning layout, image placement, shapes, and text length. Intelligent padding, calculating sizes correctly for positioning is extremely important.
{{
  "title": "Template Title",
  "theme": {{
    "name": "Custom Topic Theme",
    "mode": "dark",
    "palette": {{
      "background": "#0b0b1f",
      "surface": "#1b1b34",
      "primary": "#ff6b7a",
      "secondary": "#6c63ff",
      "accent": "#ffa94d",
      "text": "#f8f7ff",
      "muted": "#b4b2d1"
    }},
    "fonts": {{
      "heading": "Space Grotesk",
      "body": "Inter"
    }},
    "style_notes": "Short phrase characterizing the aesthetics"
  }},
  "slides": [
    {{
      "title": "Short slide title",
      "slide_type": "hero",
      "layout": "split",
      "content": {{
        "heading": "Slide Heading with placeholders like {{StudentName}}",
        "subheading": "Supporting subheading with {{Placeholder}}",
        "bullet_points": ["Point 1 with {{Placeholder}}", "Point 2", "Point 3"],
        "steps": ["Step 1", "Step 2", "Step 3"],
        "stats": [{{ "label": "Metric", "value": "42", "unit": "%", "note": "YoY" }}]
      }},
      "visual_elements": {{
        "image_query": "Specific image search query",
        "icon_query": ["simple icon keyword", "optional second keyword"],
        "shape_type": ["circle", "hexagon", "arrow"]
      }}
    }}
  ]
}}

Rules:
- Include placeholders using double curly braces, e.g., {{StudentName}}, {{Class}}, {{Division}}, {{SchoolName}}, {{Date}}
- For school templates, include a cover slide with placeholders for StudentName, Class, Division, SchoolName
- Use kid-friendly prompts and bright colors for LKG/UKG or early grades (balloons, ribbons, flowers, cartoons)
- For general templates, keep layout clean and professional
- Must include these slide types at least once when {num_slides} >= 6:
  hero, process, timeline, infographic, stats, comparison
- Use layout values only from: grid, zigzag, circular, left-right, split
- Image queries should be descriptive and relevant to the topic
- Provide 1-2 simple icon keywords per slide in icon_query
- Use 4-6 bullet points per content slide (8-14 words each)
- Subheading should be 12-20 words and add meaning
- CRITICAL: Generate a custom "theme" object utilizing precise HEX colors natively that uniquely matches the tone and intent of the template topic.
- Choose ONLY from these safe fonts: "Space Grotesk", "Inter", "Manrope", "Sora", "DM Sans", "Playfair Display"
- IMPORTANT: Vary the layouts deliberately across the presentation. Never use the same layout successively.
- Embrace rich storytelling flow across all presentation placeholders.
- Keep headings under 8 words where possible
- Keep all text short enough to fit inside the {slide_width}x{slide_height} layout and 60px margins
"""

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a presentation template about: {prompt}"},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("Failed to parse AI response as JSON")

    if "title" not in result or "slides" not in result:
        raise ValueError("AI response missing required fields")

    return result
