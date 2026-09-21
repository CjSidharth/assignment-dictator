"""Turn structured blocks into layout cues + dictation audio, one track per question."""
import functools
import operator
import re
from pathlib import Path

from pydub import AudioSegment

from . import chunker, tts


def split_into_questions(blocks: list[dict]) -> list[list[dict]]:
    """A new top-level heading starts a new question; no headings -> one question."""
    questions: list[list[dict]] = []
    current: list[dict] = []
    for b in blocks:
        if b["type"] == "heading" and current:
            questions.append(current)
            current = [b]
        else:
            current.append(b)
    if current:
        questions.append(current)
    return questions or [blocks]


def blocks_to_items(blocks: list[dict]) -> list[dict]:
    """Each item: {cue, phrase, is_diagram}. cue is a layout announcement, phrase is None for diagrams."""
    items = []
    for b in blocks:
        text = b.get("text", "").strip()
        if not text:
            continue
        if b["type"] == "diagram":
            title = re.sub(r"^\[?DIAGRAM:\s*", "", text, flags=re.IGNORECASE).rstrip("]")
            items.append({"cue": f"Diagram: {title}, draw it now", "phrase": None, "is_diagram": True})
            continue

        cue = None
        if b["type"] == "heading":
            cue = "Heading"
        elif b["type"] == "numbered_item":
            m = re.match(r"^(\d+)[.)]", text)
            cue = f"Point {m.group(1)}" if m else "Point"
            text = re.sub(r"^\d+[.)]\s*", "", text)
        elif b["type"] == "bullet":
            cue = "New line"

        for i, phrase in enumerate(chunker.split_phrases(text)):
            items.append({"cue": cue if i == 0 else None, "phrase": phrase, "is_diagram": False})
    return items


def build_question_track(
    blocks: list[dict],
    backend: str,
    voice: str,
    spw: float,
    diagram_pause: float,
    stop_at_diagrams: bool,
    tts_cache_dir: Path,
) -> list[AudioSegment]:
    items = blocks_to_items(blocks)
    parts: list[list[AudioSegment]] = [[]]

    for item in items:
        seg_list = parts[-1]
        if item["cue"]:
            seg_list.append(tts.synth(item["cue"], voice, backend, tts_cache_dir))
            seg_list.append(AudioSegment.silent(duration=400))
        if item["is_diagram"]:
            if stop_at_diagrams:
                parts.append([])
            else:
                seg_list.append(AudioSegment.silent(duration=int(diagram_pause * 1000)))
            continue
        spoken = chunker.speakify(item["phrase"])
        seg_list.append(tts.synth(spoken, voice, backend, tts_cache_dir))
        pause_ms = int(len(item["phrase"].split()) * spw * 1000)
        seg_list.append(AudioSegment.silent(duration=pause_ms))

    tracks = [
        functools.reduce(operator.add, seg_list, AudioSegment.empty())
        for seg_list in parts
        if seg_list
    ]
    return tracks or [AudioSegment.silent(duration=500)]


def export_question(track: AudioSegment, out_path: Path, title: str, album: str) -> None:
    track.export(out_path, format="mp3", tags={"title": title, "album": album, "artist": "dictate"})


def combine(question_paths: list[Path], out_path: Path, album: str) -> None:
    gap = AudioSegment.silent(duration=1000)
    combined = functools.reduce(
        operator.add, (AudioSegment.from_file(p) + gap for p in question_paths), AudioSegment.empty()
    )
    combined.export(out_path, format="mp3", tags={"title": album, "album": album, "artist": "dictate"})
