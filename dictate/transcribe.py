"""Two-stage OCR: Stage A gets a faithful markdown transcript from the vision model,
Stage B turns that markdown into structured blocks (heading/paragraph/bullet/numbered_item/diagram).
"""
import hashlib
import io
import json
import re
import time
from pathlib import Path

from PIL import Image

from . import cache, vision

STAGE_A_PROMPT = """Transcribe this handwritten page exactly as written, in plain markdown.
Do not correct spelling or grammar, do not summarise, do not explain, and do not add anything
that is not on the page. No commentary before or after the transcription.
Mark any diagram, drawing, or figure as [DIAGRAM: short title].
Mark any word you cannot read as [?].
Preserve headings, numbered items, and bullet points as they appear on the page.
Ignore any page-corner stamp box (name, page number, date, roll number, or similar
printed/ruled boilerplate) — do not transcribe it.
Never use markdown tables or pipe characters."""

STAGE_B_PROMPT_TMPL = """Convert the following transcribed markdown into structured JSON blocks.
Do not change, correct, or reword any text. Respond with ONLY a JSON object of the exact form:
{{"blocks": [{{"type": "heading|paragraph|bullet|numbered_item|diagram", "text": "...", "level": 1}}]}}
(the "level" field only applies to headings; omit it otherwise.)

Markdown:
---
{md}
---"""

BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["heading", "paragraph", "bullet", "numbered_item", "diagram"],
                    },
                    "text": {"type": "string"},
                    "level": {"type": "integer"},
                },
                "required": ["type", "text"],
            },
        }
    },
    "required": ["blocks"],
}

_PREAMBLE_RE = re.compile(r"^(here'?s|here is|sure,?|okay,?|note:).{0,80}:$", re.IGNORECASE)


def strip_think(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I).strip()
    lines = text.splitlines()
    if lines and _PREAMBLE_RE.match(lines[0].strip()):
        lines = lines[1:]
    return "\n".join(lines).strip()


def regex_parse_markdown(markdown: str) -> list[dict]:
    """Fallback (and also the parser used to build audio straight from an edited .md)."""
    blocks = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line or re.match(r"^<!--.*-->$", line):
            continue
        if line.startswith("|") and line.endswith("|"):
            # a markdown table row — never real handwritten content in this pipeline,
            # just a model's mis-rendering of a stamp box, ruled margin, or diagram frame.
            continue
        if m := re.match(r"^(#{1,6})\s*(.+)", line):
            blocks.append({"type": "heading", "text": m.group(2), "level": len(m.group(1))})
        elif m := re.match(r"^\[DIAGRAM:\s*(.+?)\]$", line, re.IGNORECASE):
            blocks.append({"type": "diagram", "text": m.group(1)})
        elif re.match(r"^[-*]\s+", line):
            blocks.append({"type": "bullet", "text": re.sub(r"^[-*]\s+", "", line)})
        elif re.match(r"^\d+[.)]\s+", line):
            blocks.append({"type": "numbered_item", "text": line})
        else:
            blocks.append({"type": "paragraph", "text": line})
    return blocks


def stage_a(backend: str, model: str, image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    text = vision.chat(backend, model, STAGE_A_PROMPT, image_bytes=buf.getvalue())
    return strip_think(text)


def stage_b(backend: str, model: str, markdown: str) -> list[dict]:
    try:
        text = vision.chat(backend, model, STAGE_B_PROMPT_TMPL.format(md=markdown), json_schema=BLOCK_SCHEMA)
        data = json.loads(strip_think(text))
        blocks = data.get("blocks", [])
        if blocks:
            return blocks
    except Exception:
        pass
    return regex_parse_markdown(markdown)


def transcribe_page(image: Image.Image, backend: str, model: str, cache_dir: Path) -> tuple[str, list[dict]]:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    key = hashlib.sha256(buf.getvalue() + f"{backend}:{model}".encode()).hexdigest()
    cached = cache.get(cache_dir, key)
    if cached:
        return cached["markdown"], cached["blocks"]
    md = stage_a(backend, model, image)
    blocks = stage_b(backend, model, md)
    cache.set(cache_dir, key, {"markdown": md, "blocks": blocks})
    return md, blocks


def transcribe_pdf(
    images: list[Image.Image], backend: str, model: str, cache_dir: Path
) -> list[tuple[str, list[dict]]]:
    pages = []
    total = len(images)
    start = time.time()
    for i, img in enumerate(images):
        pages.append(transcribe_page(img, backend, model, cache_dir))
        elapsed = time.time() - start
        avg = elapsed / (i + 1)
        eta = avg * (total - i - 1)
        print(f"\r  page {i + 1}/{total}  ETA {eta:.0f}s", end="", flush=True)
    print()
    return pages
