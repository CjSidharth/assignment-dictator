"""dictate --calibrate: play a sample paragraph, time how long the user takes to write it by hand."""
import time

from pydub.playback import play

from . import tts
from .config import TTS_CACHE_DIR, load_config, save_config

CALIBRATION_TEXT = (
    "The quick brown fox jumps over the lazy dog near the river bank while the sun "
    "sets slowly behind the distant mountains and birds fly home."
)


def calibrate() -> None:
    cfg = load_config()
    backend = tts.choose_backend(cfg.get("offline", False))
    voice = cfg["kokoro_voice"] if backend == "kokoro" else cfg["voice"]

    print("Playing a sample paragraph. Get your pen ready...")
    audio = tts.synth(CALIBRATION_TEXT, voice, backend, TTS_CACHE_DIR)
    play(audio)

    print("Now write it out by hand. Press Enter the instant you finish.")
    start = time.time()
    input()
    elapsed = time.time() - start

    words = len(CALIBRATION_TEXT.split())
    cfg["spw"] = round(elapsed / words, 2)
    save_config(cfg)
    print(f"Saved seconds_per_word = {cfg['spw']}")
