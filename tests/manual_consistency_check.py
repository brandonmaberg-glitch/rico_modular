"""Manual consistency checks for the one-brain orchestrator."""
from __future__ import annotations

from pathlib import Path

from rico.conversation.orchestrator import should_respond


SAMPLES = {
    "hello": True,
    "hi": True,
    "ok": False,
    "thanks": False,
    "what time is it": True,
    "tell me more": False,
    "can you help": True,
    "": False,
}


def check_should_respond() -> None:
    print("should_respond checks:")
    for text, expected in SAMPLES.items():
        result = should_respond(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"- {status}: {text!r} -> {result} (expected {expected})")


def check_imports() -> None:
    print("orchestrator import checks:")
    paths = [
        Path("run_rico.py"),
        Path("server/app.py"),
    ]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        status = "PASS" if "conversation.orchestrator" in content else "FAIL"
        print(f"- {status}: {path}")


if __name__ == "__main__":
    check_should_respond()
    check_imports()
