# dictate

Turn a PDF of handwritten notebook photos into dictation audio you can copy by hand —
fully local, fully free.

Pipeline: PDF pages → local vision model (via Ollama) transcribes them → you review/fix
the transcript → text is chunked into dictation phrases → text-to-speech reads it back
with pacing and layout cues (`Heading`, `Point 2`, `Diagram: ..., draw it now`) → one
MP3 per question plus a combined track.

## Install

You need three things: Python 3.10+, [Ollama](https://ollama.com) (runs the vision
model), and [ffmpeg](https://ffmpeg.org) (used by `pydub` to write MP3s).

### macOS

```bash
brew install ollama ffmpeg python@3.11
ollama serve &
ollama pull qwen3-vl:8b      # or qwen3-vl:4b / qwen3-vl:2b, see "Which --tier" below
```

### Windows

1. Install [Ollama for Windows](https://ollama.com/download/windows) and launch it once
   (it runs the server in the background from then on).
2. Install [ffmpeg](https://ffmpeg.org/download.html) and add it to your `PATH`.
3. Install [Python 3.10+](https://www.python.org/downloads/) from python.org.
4. Open PowerShell:

```powershell
ollama pull qwen3-vl:8b
```

### Both platforms — install the tool

With [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv venv
uv pip install -e .
```

Or with plain pip:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

This installs the `dictate` command into your virtualenv.

## Which `--tier` to pick

| RAM / hardware              | `--tier` | Model         |
|------------------------------|----------|---------------|
| Mac 16GB+ RAM, or a GPU PC    | `high`   | `qwen3-vl:8b` |
| 8–16GB RAM, no GPU            | `mid`    | `qwen3-vl:4b` |
| 8GB RAM, weak/old CPU-only PC | `low`    | `qwen3-vl:2b` |

`--tier` just picks the default model; `--model` overrides it outright (e.g.
`--model deepseek-ocr` for a faster alternative, or any other vision model you've pulled).

**Real-world timing** (measured on an M5 MacBook Air, GPU-accelerated): `qwen3-vl:4b`
took ~4 minutes *per page* (two model calls: transcribe, then structure). `qwen3-vl:8b`
was noticeably slower still, and both make the machine run hot under sustained use. For
one or two assignments that's fine left running in the background; for a large batch
(dozens of assignments) local inference on a laptop is genuinely impractical — see the
two options below.

## Usage

```bash
dictate DS_1.pdf                              # full pipeline, pauses for you to fix DS_1.md
dictate ./assignments/ --tier mid --spw 1.6 --offline
dictate --calibrate                           # measure your real writing speed
dictate DS_1.md                               # skip OCR, just build audio from a transcript
```

Flags:

- `--backend {ollama,gemini}` — where transcription runs (default `ollama`, see below)
- `--tier {high,mid,low}` / `--model NAME` — which vision model to transcribe with
- `--ollama-host URL` — use a remote Ollama server instead of localhost (see below)
- `--spw SECONDS` — pause length per word when dictating (default 1.8; set your own with `--calibrate`)
- `--diagram-pause SECONDS` — pause length at a `[DIAGRAM: ...]` (default 90)
- `--stop-at-diagrams` — instead of pausing, split the track into a new file at each diagram
- `--offline` — force the offline TTS backend (Kokoro) instead of edge-tts
- `--no-review` — skip the "fix the transcript" pause
- `--voice NAME` — edge-tts voice (default `en-IN-NeerjaNeural`)

### Speeding up a large batch: remote Ollama or Gemini

Two ways out if local inference on your own laptop is too slow/hot for a big batch:

**A friend's GPU rig.** Ollama can be reached over the network — no code changes needed:

```bash
# on the friend's machine (RTX 5060 / Core Ultra 9, say):
OLLAMA_HOST=0.0.0.0:11434 ollama serve
ollama pull qwen3-vl:8b

# on your machine:
dictate ./assignments/ --ollama-host http://<friend's-ip>:11434
```

Everything else about the pipeline is identical — same models, same "local and free"
guarantee, just borrowed compute. Only do this on a network you trust (Ollama has no
built-in auth), and their firewall needs to allow the port.

**Gemini's free tier.** `--backend gemini` sends each page to Google's
[Gemini API](https://ai.google.dev) instead of a local model — much faster, no hardware
needed, but **your handwritten content leaves your machine and goes to Google's
servers**. Worth knowing before you point 30 assignments' worth of notes at it. Get a
free API key (no card required) at https://aistudio.google.com/apikey, then:

```bash
export GEMINI_API_KEY=your-key-here
dictate DS_1.pdf --backend gemini
```

Check [ai.google.dev's current rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
for the free tier before a big batch — they change over time and cap requests per
minute/day. `--model` overrides the default (`gemini-3.6-flash`) if you want a different
Gemini model.

### The review step

After OCR, `dictate` writes an editable `DS_1.md` next to your PDF and stops, so you can
fix any mistakes — especially anything marked `[?]` (a word the model couldn't read).
Audio is always generated from this edited file, never straight from the model's raw
output. Press Enter when you're done editing, or pass `--no-review` to skip the pause
entirely (useful for batch/CI runs, or once you trust the transcript).

### Offline TTS (Kokoro)

`dictate` uses `edge-tts` (free, needs internet) by default, and automatically falls
back to the offline [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) engine when
there's no internet, or always when you pass `--offline`. The first time you use it,
download the two model files it needs (~326MB) into `~/.dictate/models/kokoro/` — the
tool prints the exact `curl` commands if they're missing.

### Caching

Both OCR results (keyed by a hash of the page image) and TTS audio (keyed by a hash of
the exact text spoken) are cached under `~/.dictate/cache/`. Reruns and interrupted runs
never redo work that's already done; changing `--spw` or `--diagram-pause` only changes
silence between clips, not the clips themselves, so it's instant.

## What audio you'll hear

- Layout cues before blocks: "Heading", "Point 2", "New line", "Diagram: Cluster
  Computing, draw it now"
- Symbols are read as words but you write the symbol: `&` → "and sign", `→` → "arrow"
- Acronyms are spelled slowly: "T-C-P", "M-Q-T-T"
- Technical multi-word terms are never split across phrases: "Remote Procedure Call",
  "IP address", etc. (see `TECH_TERMS` in `dictate/chunker.py` to add more)

## Development

```bash
python tests/test_dictate.py
```
