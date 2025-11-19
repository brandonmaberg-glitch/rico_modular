"""Conversation loop behaviour tests."""
from __future__ import annotations

import unittest

from run_rico import _run_conversation_loop
from stt.base import TranscriptionResult


class DummyTTS:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class DummyRouter:
    def __init__(self) -> None:
        self.received: list[str] = []

    def route(self, text: str) -> str:
        self.received.append(text)
        return f"echo: {text}"


class DummySTT:
    def __init__(self, results: list[TranscriptionResult]) -> None:
        self._results = results

    def transcribe(self, timeout: float | None = None):
        if self._results:
            return self._results.pop(0)
        return TranscriptionResult(text="", timed_out=True)


class ConversationLoopTests(unittest.TestCase):
    def test_conversation_runs_until_exit_phrase(self) -> None:
        stt = DummySTT(
            [
                TranscriptionResult(text="Hello there", timed_out=False),
                TranscriptionResult(text="That's all, RICO.", timed_out=False),
            ]
        )
        tts = DummyTTS()
        router = DummyRouter()

        _run_conversation_loop(stt, tts, router, silence_timeout=5)

        self.assertIn("echo: Hello there", tts.spoken)
        self.assertEqual(tts.spoken[-1], "Very well, Sir.")
        self.assertEqual(router.received, ["Hello there"])

    def test_silence_timeout_exits(self) -> None:
        stt = DummySTT([TranscriptionResult(text="", timed_out=True)])
        tts = DummyTTS()
        router = DummyRouter()

        _run_conversation_loop(stt, tts, router, silence_timeout=0.1)

        self.assertEqual(tts.spoken, ["Very well, Sir."])
        self.assertEqual(router.received, [])

    def test_blank_input_prompts_retry(self) -> None:
        stt = DummySTT(
            [
                TranscriptionResult(text="   ", timed_out=False),
                TranscriptionResult(text="rico, stop listening", timed_out=False),
            ]
        )
        tts = DummyTTS()
        router = DummyRouter()

        _run_conversation_loop(stt, tts, router, silence_timeout=5)

        self.assertEqual(tts.spoken[0], "I am terribly sorry Sir, I did not catch that.")
        self.assertEqual(tts.spoken[-1], "Very well, Sir.")
        self.assertEqual(router.received, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

