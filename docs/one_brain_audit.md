<!--
# Audit Report

## Current control flow traces

### CLI voice
- `run_rico.py` -> `_run_conversation_loop`
- `stt/base.py` -> `SpeechToTextEngine.transcribe` / VAD shortcut
- `rico_app.handle_text`
- `tts/speaker.py`

### UI mic
- `rico_ui/core.js` -> `POST /api/voice_ptt`
- `server/app.py` -> `rico_app.handle_voice_ptt`
- `rico/voice/vad_input.py` -> VAD recorder
- `rico/voice/transcribe.py` -> transcription
- `rico_app.handle_text`
- `_build_audio_file` -> TTS output URL

### UI text
- `rico_ui/core.js` -> `POST /api/chat`
- `server/app.py` -> `rico_app.handle_text`
- `_build_audio_file` -> TTS output URL

## Duplicated or diverging logic
- Response gating (`should_respond`) existed only in `run_rico.py`, so web paths never gated acknowledgements.
- Follow-up logic (timeout windows and second-chance) existed only in the CLI loop.
- Voice capture defaults were split between `stt/base.py` (CLI shortcut) and `rico/app.py` (web VAD), with no shared constants.
- “No speech / no transcript” outcomes were handled in the web endpoint but not uniformly for CLI follow-ups.
- Empty replies still triggered TTS in CLI because `tts_engine.speak` was called unconditionally.
- Conversation history clearing was scoped to the CLI loop and not shared by web.

## Why it causes drift
- The CLI gated acknowledgements and asked a second-chance follow-up; the web UI always replied and never re-listened.
- Follow-up timeouts in CLI were hard-coded and not shared with web.
- VAD configuration lived in two places, making tuning inconsistent.
- Empty replies could still hit the TTS path in CLI but not in web.

## Recommended consolidation points
- Centralize gating, follow-up policy, and voice capture defaults in one orchestrator module.
- Route `/api/chat`, `/api/voice_ptt`, and the CLI loop through the same orchestrator functions.
- Enforce “skip TTS on empty reply” by checking `TurnResult.reply` in both CLI and web.
- Have UI follow-up logic consume `should_followup` and `followup_timeout_ms` from the server response.
-->
