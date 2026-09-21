import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dictate import assemble, chunker
from dictate import transcribe as tr


def test_split_phrases_keeps_technical_terms_together():
    phrases = chunker.split_phrases("An IP address is assigned to every Operating System device on the network.")
    joined = " ".join(phrases)
    assert "IP address" in joined
    assert "Operating System" in joined
    assert all(p.strip() for p in phrases)


def test_speakify_symbols_and_acronyms():
    out = chunker.speakify("A & B -> TCP")
    assert "and sign" in out
    assert "arrow" in out
    assert "T-C-P" in out


def test_regex_parse_markdown_blocks():
    md = "# Heading\n- a bullet\n1. first item\n[DIAGRAM: Network Diagram]\nJust a paragraph."
    blocks = tr.regex_parse_markdown(md)
    assert [b["type"] for b in blocks] == ["heading", "bullet", "numbered_item", "diagram", "paragraph"]


def test_regex_parse_markdown_drops_table_rows():
    md = "| GOPI |\n| Page No.: |\nQ1 Real content here."
    blocks = tr.regex_parse_markdown(md)
    assert len(blocks) == 1
    assert blocks[0]["text"] == "Q1 Real content here."


def test_split_into_questions_by_heading():
    blocks = [
        {"type": "heading", "text": "Q1"},
        {"type": "paragraph", "text": "answer one"},
        {"type": "heading", "text": "Q2"},
        {"type": "paragraph", "text": "answer two"},
    ]
    questions = assemble.split_into_questions(blocks)
    assert len(questions) == 2
    assert questions[0][0]["text"] == "Q1"
    assert questions[1][0]["text"] == "Q2"


def main():
    test_split_phrases_keeps_technical_terms_together()
    test_speakify_symbols_and_acronyms()
    test_regex_parse_markdown_blocks()
    test_regex_parse_markdown_drops_table_rows()
    test_split_into_questions_by_heading()
    print("all tests passed")


if __name__ == "__main__":
    main()
