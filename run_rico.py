"""Runtime entry point for the RICO assistant."""
from __future__ import annotations

import logging

import core.skill_loader as SkillLoader
from config.settings import AppConfig
from core.skill_registry import SkillRegistry
from logs.logger import setup_logger
from router.command_router import CommandRouter
from skills import car_info, conversation, system_status, web_search
from stt.base import SpeechToTextEngine, TranscriptionResult
from tts.speaker import Speaker
from ui_bridge import (
    launch_ui,
    send_listening,
    send_reply,
    send_thinking,
    send_transcription,
    start_ui_server,
)
from wakeword.engine import WakeWordEngine


logger = logging.getLogger("RICO")


def build_skill_registry(config: AppConfig):
    """Create the mapping of skill names to callable handlers."""
    registry = SkillRegistry()
    loaded_skills = SkillLoader.load_skills()

    for skill in loaded_skills:
        registry.register(skill.__class__)

    loaded_skill_names = [skill.__class__.__name__ for skill in loaded_skills]
    logger.info("Loaded skills: %s", ", ".join(loaded_skill_names) or "none")

    return {
        "system_status": system_status.activate,
        "conversation": conversation.activate,
        "car_info": car_info.activate,
        "web_search": web_search.run_web_search,
    }


def main() -> None:
    """Start the assistant."""
    global logger
    config = AppConfig.load()
    logger = setup_logger()
    logger.info("Initialising RICO...")

    start_ui_server()
    launch_ui()

    wake_engine = WakeWordEngine()
    stt_engine = SpeechToTextEngine(config.openai_api_key)
    tts_engine = Speaker(
        openai_api_key=config.openai_api_key,
        elevenlabs_api_key=config.elevenlabs_api_key,
        voice_id=config.elevenlabs_voice_id,
    )
    router = CommandRouter(build_skill_registry(config))

    logger.info("RICO is online. Awaiting your command, Sir.")

    while True:
        try:
            if not wake_engine.wait_for_wakeword():
                logger.info("Wakeword listener stopped. Shutting down.")
                break

            logger.info("Wakeword detected. Entering conversation mode...")
            _run_conversation_loop(
                stt_engine=stt_engine,
                tts_engine=tts_engine,
                router=router,
                silence_timeout=20.0,
            )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Exiting gracefully.")
            break
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Unexpected error: %s", exc)
            tts_engine.speak(
                "Apologies Sir, an error occurred but I remain attentive."
            )

    logger.info("RICO has powered down.")


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


def _run_conversation_loop(
    stt_engine: SpeechToTextEngine,
    tts_engine: Speaker,
    router: CommandRouter,
    silence_timeout: float,
) -> None:
    """Maintain an active conversation until an exit condition is met."""

    while True:
        send_listening(True)
        transcription = stt_engine.transcribe(timeout=silence_timeout)
        if isinstance(transcription, TranscriptionResult):
            result = transcription
        else:  # pragma: no cover - defensive for legacy return
            result = TranscriptionResult(text=str(transcription), timed_out=False)

        if result.timed_out:
            logger.info(
                "Silence timeout reached after %.0f seconds; exiting conversation mode.",
                silence_timeout,
            )
            tts_engine.speak("Very well, Sir.")
            send_listening(False)
            break

        text = result.text.strip()
        logger.info("Transcription: %s", text)
        send_transcription(text)

        if not text:
            logger.warning("No speech detected.")
            tts_engine.speak("I am terribly sorry Sir, I did not catch that.")
            continue

        normalised = _normalise_command(text)

        if normalised.startswith("voice"):
            if _handle_voice_command(normalised, tts_engine):
                continue

        if _should_exit(text):
            logger.info("Exit phrase detected; ending conversation mode.")
            tts_engine.speak("Very well, Sir.")
            send_listening(False)
            break

        send_thinking(0.85)
        response = router.route(text)
        logger.info("Skill response: %s", response)
        send_thinking(0.0)
        send_reply(response)
        tts_engine.speak(response)


if __name__ == "__main__":
    main()
