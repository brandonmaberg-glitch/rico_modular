"""Conversation loop behaviour tests."""
from __future__ import annotations

import unittest

from run_rico import _run_conversation_loop
from stt.base import TranscriptionResult


class DummyTTS:
    def __init__(self) -> None:
        self.spoken: list[tuple[str, str]] = []
        self.provider = "openai"

    def switch_to_elevenlabs(self) -> bool:
        self.provider = "elevenlabs"
        return True

    def switch_to_openai(self) -> bool:
        self.provider = "openai"
        return True

    def speak(self, text: str) -> None:
        self.spoken.append((self.provider, text))


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

        self.assertIn(("openai", "echo: Hello there"), tts.spoken)
        self.assertEqual(tts.spoken[-1], ("openai", "Very well, Sir."))
        self.assertEqual(router.received, ["Hello there"])

    def test_silence_timeout_exits(self) -> None:
        stt = DummySTT([TranscriptionResult(text="", timed_out=True)])
        tts = DummyTTS()
        router = DummyRouter()

        _run_conversation_loop(stt, tts, router, silence_timeout=0.1)

        self.assertEqual(tts.spoken, [("openai", "Very well, Sir.")])
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

        self.assertEqual(tts.spoken[0], ("openai", "I am terribly sorry Sir, I did not catch that."))
        self.assertEqual(tts.spoken[-1], ("openai", "Very well, Sir."))
        self.assertEqual(router.received, [])

    def test_voice_command_switches_to_elevenlabs(self) -> None:
        stt = DummySTT(
            [
                TranscriptionResult(text="Voice elevenlabs.", timed_out=False),
                TranscriptionResult(text="Hello there", timed_out=False),
                TranscriptionResult(text="that's all, rico", timed_out=False),
            ]
        )
        tts = DummyTTS()
        router = DummyRouter()

        _run_conversation_loop(stt, tts, router, silence_timeout=5)

        self.assertEqual(tts.spoken[0], ("elevenlabs", "Switching to your ElevenLabs voice, Sir."))
        self.assertEqual(tts.spoken[1], ("elevenlabs", "echo: Hello there"))
        self.assertEqual(tts.spoken[-1], ("elevenlabs", "Very well, Sir."))
        self.assertEqual(router.received, ["Hello there"])

    def test_voice_command_switches_back_to_openai(self) -> None:
        stt = DummySTT(
            [
                TranscriptionResult(text="Voice eleven labs", timed_out=False),
                TranscriptionResult(text="voice openai", timed_out=False),
                TranscriptionResult(text="that's all, rico", timed_out=False),
            ]
        )
        tts = DummyTTS()
        router = DummyRouter()

        _run_conversation_loop(stt, tts, router, silence_timeout=5)

        self.assertEqual(tts.spoken[0], ("elevenlabs", "Switching to your ElevenLabs voice, Sir."))
        self.assertEqual(tts.spoken[1], ("openai", "Reverting to the OpenAI voice, Sir."))
        self.assertEqual(tts.spoken[-1], ("openai", "Very well, Sir."))
        self.assertEqual(router.received, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

