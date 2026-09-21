"""Orchestrates one input file: PDF -> transcript -> review -> audio, or .md -> audio directly."""
from pathlib import Path

from . import assemble, ollama_check, pdf, review, transcribe, tts, vision
from .config import OCR_CACHE_DIR, TTS_CACHE_DIR


def process(path: Path, model: str, cfg: dict) -> None:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        md_path = path.with_suffix(".md")
        backend = cfg["backend"]
        if backend == "gemini":
            vision.check_gemini_key()
        else:
            ollama_check.check_ollama(model)
        print(f"Rendering pages from {path.name}...")
        images = pdf.pdf_to_images(path)
        pages = transcribe.transcribe_pdf(images, backend, model, OCR_CACHE_DIR)
        review.write_transcript_md(pages, md_path)
        review.pause_for_review(md_path, cfg["no_review"])
    elif suffix == ".md":
        md_path = path
    else:
        print(f"Skipping unsupported file: {path}")
        return

    build_audio(md_path, cfg)


def build_audio(md_path: Path, cfg: dict) -> None:
    blocks = transcribe.regex_parse_markdown(md_path.read_text())
    questions = assemble.split_into_questions(blocks)

    backend = tts.choose_backend(cfg["offline"])
    voice = cfg["kokoro_voice"] if backend == "kokoro" else cfg["voice"]
    stem = md_path.stem
    out_dir = md_path.parent

    print(f"Synthesizing audio with {backend} backend...")
    question_paths = []
    for i, qblocks in enumerate(questions, 1):
        tracks = assemble.build_question_track(
            qblocks, backend, voice, cfg["spw"], cfg["diagram_pause"], cfg["stop_at_diagrams"], TTS_CACHE_DIR
        )
        multi = len(tracks) > 1
        for j, track in enumerate(tracks, 1):
            suffix = f"_Q{i}" + (f"_{j}" if multi else "")
            out_path = out_dir / f"{stem}{suffix}.mp3"
            title = f"{stem} Q{i}" + (f" part {j}" if multi else "")
            assemble.export_question(track, out_path, title, stem)
            question_paths.append(out_path)
            print(f"  wrote {out_path.name}")

    combined_path = out_dir / f"{stem}_combined.mp3"
    assemble.combine(question_paths, combined_path, stem)
    print(f"  wrote {combined_path.name}")
