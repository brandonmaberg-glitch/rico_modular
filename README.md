# RICO (Really Intelligent Car Operator)

RICO is a modular voice assistant tailored for automotive scenarios. The current
build provides a complete Python project skeleton with wakeword detection,
speech-to-text (STT), text-to-speech (TTS), command routing, and a skills system
that can be extended easily.

## Features

- Jarvis-style British butler personality that addresses Mr Berg.
- Placeholder wakeword engine that listens for a configurable keyword.
- Speech-to-text pipeline using OpenAI Whisper/Realtime APIs with console
  fallback.
- ElevenLabs text-to-speech integration with graceful degradation.
- Skill-based command router with starter skills for system status, web search,
  conversation, and vehicle information.
- Centralized logging, configuration management, and personality prompts.

## Project Structure

```
run_rico.py                Main runtime loop
config/                    Environment-driven configuration objects
wakeword/                  Wakeword detection engine (placeholder today)
stt/                       Speech-to-text interfaces
tts/                       Text-to-speech helpers
router/                    Command router that dispatches to skills
skills/                    Pluggable skills with activate() entry points
personality/               Persona and prompt assets
utils/                     Shared helpers (logging, etc.)
logs/                      Default log output directory
```

## Getting Started

1. **Install Python 3.12+** and a virtual environment.

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** (optional but recommended):

   ```bash
   export OPENAI_API_KEY="sk-..."
   export ELEVENLABS_API_KEY="..."
   export ELEVENLABS_VOICE_ID="..."  # optional, defaults to Rachel
   export RICO_WAKEWORD="wake"        # optional custom wakeword
   export RICO_LOG_DIR="logs"         # optional log destination
   ```

4. **Run RICO**:

   ```bash
   python run_rico.py
   ```

   - Type the wakeword (default `wake`) to trigger the assistant.
   - Dictate a command in the console when prompted.
   - RICO routes the command to the best skill and speaks/logs the result.

## Extending RICO

- Create a new file under `skills/` with an `activate(text: str) -> str` function.
- Register the skill inside `run_rico.py` using `router.register_skill(...)`.
- Update the routing logic in `router/command_router.py` as necessary.

## Logging

Logs are stored in the `logs/` directory by default with rotation support.

## Disclaimer

This build uses console I/O placeholders for wakeword, STT, and TTS to keep the
project runnable everywhere. Swap in real microphone and playback hooks as you
connect actual hardware.
