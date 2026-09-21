import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".dictate"
CACHE_DIR = CONFIG_DIR / "cache"
OCR_CACHE_DIR = CACHE_DIR / "ocr"
TTS_CACHE_DIR = CACHE_DIR / "tts"
CONFIG_FILE = CONFIG_DIR / "config.json"

KOKORO_DIR = CONFIG_DIR / "models" / "kokoro"
KOKORO_MODEL = KOKORO_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES = KOKORO_DIR / "voices-v1.0.bin"

TIER_MODELS = {
    "high": "qwen3-vl:8b",
    "mid": "qwen3-vl:4b",
    "low": "qwen3-vl:2b",
}

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

DEFAULTS = {
    "tier": "high",
    "backend": "ollama",
    "spw": 1.8,
    "diagram_pause": 90,
    "voice": "en-IN-NeerjaNeural",
    "kokoro_voice": "af_sarah",
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        cfg.update(json.loads(CONFIG_FILE.read_text()))
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def resolve_model(backend: str, tier: str | None, model: str | None) -> str:
    if model:
        return model
    if backend == "gemini":
        return DEFAULT_GEMINI_MODEL
    return TIER_MODELS.get(tier or DEFAULTS["tier"], TIER_MODELS["high"])
