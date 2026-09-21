"""Dispatches a vision/text chat call to whichever backend is selected:
- ollama: local, free, default. Talks to OLLAMA_HOST (localhost, or a friend's GPU rig).
- gemini: free-tier cloud API, opt-in. Trades "everything stays local" for speed.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

import ollama

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def check_gemini_key() -> None:
    if os.environ.get("GEMINI_API_KEY"):
        return
    print("No GEMINI_API_KEY set. Get a free key at https://aistudio.google.com/apikey, then:\n")
    print("  macOS/Linux:  export GEMINI_API_KEY=your-key-here")
    print("  Windows:      setx GEMINI_API_KEY your-key-here   (restart the terminal after)")
    sys.exit(1)


def _ollama_chat(model: str, prompt: str, image_bytes: bytes | None, json_schema: dict | None) -> str:
    content = {"role": "user", "content": prompt}
    if image_bytes is not None:
        content["images"] = [image_bytes]
    kwargs = {"model": model, "messages": [content]}
    if json_schema is not None:
        kwargs["format"] = json_schema
    resp = ollama.chat(**kwargs)
    msg = resp.get("message") if isinstance(resp, dict) else resp.message
    return msg.get("content") if isinstance(msg, dict) else msg.content


def _gemini_chat(model: str, prompt: str, image_bytes: bytes | None, json_schema: dict | None) -> str:
    check_gemini_key()
    parts = [{"text": prompt}]
    if image_bytes is not None:
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(image_bytes).decode()}})
    body = {"contents": [{"parts": parts}]}
    if json_schema is not None:
        # Ask for JSON via mime type only (the prompt itself describes the shape) —
        # skips Gemini's OpenAPI-subset responseSchema, whose type-casing rules are a
        # needless landmine when a plain "respond with only JSON" prompt already works.
        body["generationConfig"] = {"responseMimeType": "application/json"}

    req = urllib.request.Request(
        GEMINI_URL.format(model=model),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        method="POST",
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code not in (429, 500, 503, 504) or attempt == 5:
                raise RuntimeError(f"Gemini API error {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError):
            if attempt == 5:
                raise
        wait = 5 * 2**attempt
        print(f"\n  Gemini busy/unreachable, retrying in {wait}s...", flush=True)
        time.sleep(wait)


def chat(backend: str, model: str, prompt: str, image_bytes: bytes | None = None, json_schema: dict | None = None) -> str:
    fn = _gemini_chat if backend == "gemini" else _ollama_chat
    return fn(model, prompt, image_bytes, json_schema)
