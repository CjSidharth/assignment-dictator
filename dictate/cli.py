import argparse
import os
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dictate", description="Turn handwritten-assignment PDFs into dictation audio.")
    p.add_argument("input", nargs="?", help="A PDF, a Markdown transcript, or a directory of them")
    p.add_argument(
        "--backend",
        choices=["ollama", "gemini"],
        help="Transcription backend: ollama (local, free, default) or gemini (free-tier cloud, needs GEMINI_API_KEY)",
    )
    p.add_argument("--tier", choices=["high", "mid", "low"], help="Ollama model size preset (default: high)")
    p.add_argument("--model", help="Explicit model name, overrides --tier (e.g. deepseek-ocr, gemini-2.5-flash)")
    p.add_argument(
        "--ollama-host",
        help="Address of a remote Ollama server, e.g. http://192.168.1.50:11434 (a friend's GPU rig)",
    )
    p.add_argument("--spw", type=float, help="Seconds per word for dictation pauses (default: 1.8)")
    p.add_argument("--diagram-pause", type=float, help="Seconds to pause at a diagram (default: 90)")
    p.add_argument("--stop-at-diagrams", action="store_true", help="Split into a new file at each diagram")
    p.add_argument("--offline", action="store_true", help="Force offline TTS (Kokoro) instead of edge-tts")
    p.add_argument("--no-review", action="store_true", help="Skip the pause-to-edit-transcript step")
    p.add_argument("--voice", help="edge-tts voice name (default: en-IN-NeerjaNeural)")
    p.add_argument("--calibrate", action="store_true", help="Measure your real seconds-per-word and save it")
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)

    if args.ollama_host:
        # Must happen before anything imports the `ollama` package, which reads this once at import time.
        os.environ["OLLAMA_HOST"] = args.ollama_host

    if args.calibrate:
        from .calibrate import calibrate

        calibrate()
        return

    if not args.input:
        build_parser().error("input PDF, Markdown file, or directory is required (or pass --calibrate)")

    from .config import load_config, resolve_model

    cfg = load_config()
    cfg["backend"] = args.backend or cfg["backend"]
    cfg["spw"] = args.spw or cfg["spw"]
    cfg["diagram_pause"] = args.diagram_pause or cfg["diagram_pause"]
    cfg["voice"] = args.voice or cfg["voice"]
    cfg["offline"] = args.offline
    cfg["stop_at_diagrams"] = args.stop_at_diagrams
    cfg["no_review"] = args.no_review
    model = resolve_model(cfg["backend"], args.tier, args.model)

    path = Path(args.input)
    if path.is_dir():
        pdfs = sorted(path.glob("*.pdf"))
        stems = {p.stem for p in pdfs}
        # a .md next to a same-named .pdf is that PDF's own transcript, not a separate input
        targets = pdfs + [m for m in sorted(path.glob("*.md")) if m.stem not in stems]
        if not targets:
            print(f"No .pdf or .md files found in {path}")
            sys.exit(1)
    else:
        targets = [path]

    from . import pipeline

    for target in targets:
        pipeline.process(target, model, cfg)


if __name__ == "__main__":
    main()
