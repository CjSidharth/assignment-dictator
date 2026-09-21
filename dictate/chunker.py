"""Split transcript text into 4-7 word dictation phrases, and turn a phrase into
what should actually be *spoken* (symbols as words, acronyms spelled out).
"""
import re

# ponytail: explicit list rather than an NLP phrase-detector — extend this if a term keeps getting split.
TECH_TERMS = [
    "Remote Procedure Call",
    "IP address",
    "Operating System",
    "Application Programming Interface",
    "Transmission Control Protocol",
    "User Datagram Protocol",
    "Domain Name System",
    "Object Oriented Programming",
    "Data Structure",
    "Machine Learning",
    "Artificial Intelligence",
    "Central Processing Unit",
    "Random Access Memory",
    "Graphical User Interface",
    "Local Area Network",
    "Wide Area Network",
    "Structured Query Language",
]

SYMBOL_WORDS = {
    "⇒": "double arrow",
    "=>": "double arrow",
    "↳": "arrow",
    "→": "arrow",
    "->": "arrow",
    "&": "and sign",
    "%": "percent sign",
    "+": "plus sign",
    "=": "equals sign",
    "<": "less than sign",
    ">": "greater than sign",
    "#": "hash sign",
    "@": "at sign",
    "/": "slash",
    "*": "asterisk",
    "_": "underscore",
}

_TERMS_RE = re.compile(
    "(" + "|".join(re.escape(t) for t in sorted(TECH_TERMS, key=len, reverse=True)) + ")",
    re.IGNORECASE,
)


def _tokenize(text: str) -> list[tuple[str, int]]:
    """Return (token, word_count) pairs; a protected term is one token."""
    tokens = []
    for part in _TERMS_RE.split(text):
        if not part:
            continue
        if any(part.lower() == t.lower() for t in TECH_TERMS):
            tokens.append((part, part.count(" ") + 1))
        else:
            tokens.extend((w, 1) for w in part.split())
    return tokens


def split_phrases(text: str, min_words: int = 4, max_words: int = 7) -> list[str]:
    tokens = _tokenize(text)
    phrases = []
    current: list[str] = []
    count = 0
    for tok, wc in tokens:
        current.append(tok)
        count += wc
        at_boundary = tok.rstrip()[-1:] in ",.;:!?"
        if count >= max_words or (count >= min_words and at_boundary):
            phrases.append(" ".join(current))
            current, count = [], 0
    if current:
        if phrases and count < min_words:
            phrases[-1] = phrases[-1] + " " + " ".join(current)
        else:
            phrases.append(" ".join(current))
    return phrases


_ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}\b")


def speakify(phrase: str) -> str:
    """What TTS should say for a phrase: symbols become words, acronyms get spelled slowly."""
    text = phrase
    for sym, word in SYMBOL_WORDS.items():
        if sym in text:
            text = text.replace(sym, f" {word} ")
    text = _ACRONYM_RE.sub(lambda m: "-".join(m.group(0)), text)
    return re.sub(r"\s+", " ", text).strip()
