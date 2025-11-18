"""Runtime entry point for the RICO assistant."""
from __future__ import annotations

from config.settings import AppConfig
from logs.logger import setup_logger
from router.command_router import CommandRouter
from skills import car_info, conversation, system_status, web_search
from stt.base import SpeechToTextEngine
from tts.elevenlabs_tts import ElevenLabsTTS
from wakeword.engine import WakeWordEngine


def build_skill_registry(config: AppConfig):
    """Create the mapping of skill names to callable handlers."""
    return {
        "system_status": system_status.activate,
        "conversation": conversation.activate,
        "car_info": car_info.activate,
        "web_search": lambda query: web_search.activate(
            query, safe_search=config.ddg_safe_search
        ),
    }


def main() -> None:
    """Start the assistant."""
    config = AppConfig.load()
    logger = setup_logger()
    logger.info("Initialising RICO...")

    wake_engine = WakeWordEngine()
    stt_engine = SpeechToTextEngine(config.openai_api_key)
    tts_engine = ElevenLabsTTS(config.elevenlabs_api_key, config.elevenlabs_voice_id)
    router = CommandRouter(build_skill_registry(config))

    logger.info("RICO is online. Awaiting your command, Sir.")

    while True:
        try:
            if not wake_engine.wait_for_wakeword():
                logger.info("Wakeword listener stopped. Shutting down.")
                break

            logger.info("Wakeword detected. Listening...")
            transcription = stt_engine.transcribe()
            logger.info("Transcription: %s", transcription)

            if not transcription:
                logger.warning("No speech detected.")
                tts_engine.speak("I am terribly sorry Sir, I did not catch that.")
                continue

            response = router.route(transcription)
            logger.info("Skill response: %s", response)
            tts_engine.speak(response)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Exiting gracefully.")
            break
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Unexpected error: %s", exc)
            tts_engine.speak(
                "Apologies Sir, an error occurred but I remain attentive."
            )

    logger.info("RICO has powered down.")


if __name__ == "__main__":
    main()
