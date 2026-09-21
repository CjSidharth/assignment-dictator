"""Pluggable TTS: edge-tts (free, online) by default, Kokoro (offline, CPU) as fallback.
Every synthesized clip is cached to disk by hash of (backend, voice, text).
"""
import asyncio
import hashlib
import socket
import sys
from pathlib import Path

import edge_tts
from pydub import AudioSegment

from .config import KOKORO_MODEL, KOKORO_VOICES

_kokoro = None


def has_internet(timeout: float = 1.5) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout).close()
        return True
    except OSError:
        return False


def choose_backend(offline: bool) -> str:
    return "kokoro" if (offline or not has_internet()) else "edge"


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        if not (KOKORO_MODEL.exists() and KOKORO_VOICES.exists()):
            print("Kokoro model files not found. Download them with:\n")
            print(f"  mkdir -p {KOKORO_MODEL.parent}")
            print(
                f"  curl -L -o {KOKORO_MODEL} "
                "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
            )
            print(
                f"  curl -L -o {KOKORO_VOICES} "
                "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
            )
            sys.exit(1)
        from kokoro_onnx import Kokoro

        _kokoro = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
    return _kokoro


def _synth_edge(text: str, voice: str, out_path: Path) -> None:
    async def _run():
        await edge_tts.Communicate(text, voice).save(str(out_path))

    asyncio.run(_run())


def _synth_kokoro(text: str, voice: str, out_path: Path) -> None:
    import soundfile as sf

    samples, sr = _get_kokoro().create(text, voice=voice, speed=1.0, lang="en-us")
    sf.write(str(out_path), samples, sr)


def synth(text: str, voice: str, backend: str, cache_dir: Path) -> AudioSegment:
    key = hashlib.sha256(f"{backend}|{voice}|{text}".encode()).hexdigest()
    ext = "mp3" if backend == "edge" else "wav"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.{ext}"
    if not path.exists():
        (_synth_edge if backend == "edge" else _synth_kokoro)(text, voice, path)
    return AudioSegment.from_file(path)
