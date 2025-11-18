"""Main runtime for the RICO assistant."""
from __future__ import annotations

from config.settings import Settings
from wakeword.engine import WakewordEngine
from stt.transcriber import SpeechToText
from tts.speaker import TextToSpeech
from router.command_router import CommandRouter
from utils.logger import configure_logger
from skills import conversation, system_status, web_search, car_info


def bootstrap_router(logger) -> CommandRouter:
    """Instantiate the command router and register base skills."""

    router = CommandRouter(logger=logger.info)
    router.register_skill("system_status", system_status.activate)
    router.register_skill("conversation", conversation.activate)
    router.register_skill("web_search", web_search.activate)
    router.register_skill("car_info", car_info.activate)
    return router


def main() -> None:
    """Entry point for running the assistant loop."""

    settings = Settings.load_from_env()
    settings.validate()
    logger = configure_logger("RICO", settings.log_dir)

    wake_engine = WakewordEngine(settings.wakeword_phrase)
    stt_engine = SpeechToText(settings.openai_api_key)
    tts_engine = TextToSpeech(settings.elevenlabs_api_key, settings.elevenlabs_voice_id)
    router = bootstrap_router(logger)

    logger.info("RICO initialized and awaiting your call, Sir.")

    while True:
        try:
            logger.info("Listening for wakeword '%s'...", settings.wakeword_phrase)
            if not wake_engine.detect_wakeword():
                continue

            logger.info("Wakeword detected. Capturing speech...")
            transcription = stt_engine.capture_and_transcribe()
            if not transcription:
                logger.info("No transcription captured; returning to idle state.")
                continue

            logger.info("User said: %s", transcription)
            response = router.route(transcription)
            logger.info("RICO response: %s", response)
            tts_engine.speak(response)
        except KeyboardInterrupt:
            logger.info("RICO shutting down at your command, Sir.")
            break
        except Exception as exc:
            logger.exception("Unhandled error in main loop: %s", exc)


if __name__ == "__main__":
    main()
