# RICO (Really Intelligent Co Operator)

RICO is a modular, Jarvis-inspired British butler assistant implemented in Python 3.12.
It provides a pluggable wakeword listener, STT, ElevenLabs-based speech, and a skill
router that can be extended for future automations.

## Features
- Configurable wakeword engine (placeholder text trigger for now)
- Whisper/Realtime-ready STT pipeline with text fallback
- ElevenLabs text-to-speech wrapper with graceful fallback
- Keyword-based command router
- Modular skills: system status, conversation, DuckDuckGo search, and car telemetry stub
- Structured logging to `logs/rico.log`

## Project Structure
```
run_rico.py              # Runtime entry point
config/                  # Configuration objects
wakeword/                # Wakeword detection abstraction
stt/                     # Speech-to-text pipeline
tts/                     # ElevenLabs integration
router/                  # Command routing
skills/                  # Individual skill modules
logs/                    # Logging helpers and log files
personality/             # System and persona prompts
utils/                   # Shared helpers
```

## Requirements
- Python 3.12+
- Optional APIs: `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`

Install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables
Set the following if you wish to enable cloud integrations:
- `OPENAI_API_KEY` – enables Whisper/Realtime transcription.
- `ELEVENLABS_API_KEY` – enables real TTS output.
- `ELEVENLABS_VOICE_ID` – optional voice override.
- `DDG_SAFE_SEARCH` – `true/false` toggle for the DuckDuckGo skill.

## Running RICO
```bash
python run_rico.py
```
1. Type `wake` when prompted to trigger the wakeword.
2. Enter your spoken command (text fallback for now).
3. RICO routes the intent to the appropriate skill and responds via TTS/logs.

All interactions are logged to `logs/rico.log` for auditing.

## Extending Skills
Create a new module inside `skills/` with an `activate(text: str) -> str` function and
register it inside `run_rico.build_skill_registry`. The router can be updated to pattern
match additional intents or swapped out entirely for an LLM-based classifier.

## Error Handling
The runtime never exits on STT/TTS/wakeword failure; it logs issues and falls back to
text interaction, ensuring the command loop remains responsive.
