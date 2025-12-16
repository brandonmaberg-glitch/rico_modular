"""Command handling helpers for RICO."""

from __future__ import annotations

from tts.speaker import Speaker

_EXIT_PHRASES = ["rico, stop listening", "that's all, rico", "that’s all, rico"]


def _should_exit(text: str) -> bool:
    lowered = text.strip().lower()
    return any(phrase in lowered for phrase in _EXIT_PHRASES)


def _normalise_command(text: str) -> str:
    """Lowercase and strip trailing punctuation for command matching."""

    return text.strip().lower().rstrip(".,?!")


def _handle_voice_command(command: str, tts_engine: Speaker) -> bool:
    """Switch TTS provider based on the voice command provided."""

    if "eleven" in command:
        if tts_engine.switch_to_elevenlabs():
            tts_engine.speak("Switching to your ElevenLabs voice, Sir.")
        else:
            tts_engine.speak("ElevenLabs voice is unavailable, Sir.")
        return True

    if "openai" in command:
        if tts_engine.switch_to_openai():
            tts_engine.speak("Reverting to the OpenAI voice, Sir.")
        else:
            tts_engine.speak("OpenAI voice is unavailable, Sir.")
        return True

    if command == "voice":
        if tts_engine.provider == "elevenlabs":
            return _handle_voice_command("voice openai", tts_engine)
        return _handle_voice_command("voice elevenlabs", tts_engine)

    return False


__all__ = ["_handle_voice_command", "_normalise_command", "_should_exit"]
