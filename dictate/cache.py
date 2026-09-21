"""Tiny JSON cache keyed by a hash the caller computes. Used for per-page OCR results."""
import json
from pathlib import Path


def get(cache_dir: Path, key: str):
    p = cache_dir / f"{key}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def set(cache_dir: Path, key: str, value) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(json.dumps(value))
