"""Make sure Ollama is running and the chosen model is pulled, or tell the user exactly what to run."""
import platform
import sys

import ollama


def _model_names(resp) -> list[str]:
    models = getattr(resp, "models", None)
    if models is None and isinstance(resp, dict):
        models = resp.get("models", [])
    names = []
    for m in models or []:
        name = getattr(m, "model", None)
        if name is None and isinstance(m, dict):
            name = m.get("model") or m.get("name")
        if name:
            names.append(name)
    return names


def install_instructions(model: str) -> str:
    system = platform.system()
    if system == "Darwin":
        install = "brew install ollama\nollama serve"
    elif system == "Linux":
        install = "curl -fsSL https://ollama.com/install.sh | sh\nollama serve"
    else:
        install = (
            "Download and install Ollama from https://ollama.com/download/windows\n"
            "(launching the app starts the server automatically)"
        )
    return f"{install}\n\nThen pull the model:\nollama pull {model}"


def check_ollama(model: str) -> None:
    try:
        resp = ollama.list()
    except Exception:
        print("Ollama doesn't seem to be installed or running.\n")
        print(install_instructions(model))
        sys.exit(1)

    names = _model_names(resp)
    base = model.split(":")[0]
    if not any(n == model or n.startswith(base + ":") for n in names):
        print(f"Model '{model}' is not pulled yet. Run:\n  ollama pull {model}")
        sys.exit(1)
