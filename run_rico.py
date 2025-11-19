"""Runtime entry point for the RICO assistant."""
from __future__ import annotations

import logging

from config.settings import AppConfig
from logs.logger import setup_logger
from router.command_router import CommandRouter
from skills import car_info, conversation, system_status, web_search
from stt.base import SpeechToTextEngine, TranscriptionResult
from tts.speaker import Speaker
from wakeword.engine import WakeWordEngine


logger = logging.getLogger("RICO")


def build_skill_registry(config: AppConfig):
    """Create the mapping of skill names to callable handlers."""
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


def _run_conversation_loop(
    stt_engine: SpeechToTextEngine,
    tts_engine: Speaker,
    router: CommandRouter,
    silence_timeout: float,
) -> None:
    """Maintain an active conversation until an exit condition is met."""

    while True:
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
            break

        text = result.text.strip()
        logger.info("Transcription: %s", text)

        if not text:
            logger.warning("No speech detected.")
            tts_engine.speak("I am terribly sorry Sir, I did not catch that.")
            continue

        if text.lower() == "voice":
            if tts_engine.provider == "elevenlabs":
                if tts_engine.switch_to_openai():
                    tts_engine.speak("Reverting to the OpenAI voice, Sir.")
                else:
                    tts_engine.speak("OpenAI voice is unavailable, Sir.")
            else:
                if tts_engine.switch_to_elevenlabs():
                    tts_engine.speak("Switching to your ElevenLabs voice, Sir.")
                else:
                    tts_engine.speak("ElevenLabs voice is unavailable, Sir.")
            continue

        if _should_exit(text):
            logger.info("Exit phrase detected; ending conversation mode.")
            tts_engine.speak("Very well, Sir.")
            break

        response = router.route(text)
        logger.info("Skill response: %s", response)
        tts_engine.speak(response)


if __name__ == "__main__":
    main()
