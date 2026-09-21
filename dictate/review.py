"""Write the editable transcript and pause so mistakes (esp. [?] spots) get fixed before TTS."""
from pathlib import Path


def write_transcript_md(pages: list[tuple[str, list[dict]]], out_path: Path) -> None:
    lines = []
    for i, (md, _blocks) in enumerate(pages, 1):
        lines.append(f"<!-- page {i} -->")
        lines.append(md.strip())
        lines.append("")
    out_path.write_text("\n".join(lines))


def pause_for_review(md_path: Path, no_review: bool) -> None:
    flagged = md_path.read_text().count("[?]")
    if no_review:
        return
    msg = f"\nWrote {md_path}. Fix mistakes now"
    if flagged:
        msg += f" ({flagged} spot(s) marked [?] need a look)"
    print(msg + ".")
    input("Press Enter when you're done editing... ")
