const coreEl = document.getElementById('core');
const promptInput = document.getElementById('prompt');
const form = document.getElementById('core-form');
const consoleLog = document.getElementById('console-log');
const micButton = document.getElementById('mic-button');
const audioEl = document.getElementById('ricoAudio');
const enableAudioButton = document.getElementById('enable-audio');

let pendingAudioUrl = null;
let micBusy = false;
let followupSessionId = 0;
let followupAbortController = null;

function setCoreState(nextState) {
  window.coreStateController?.setCoreState(nextState);
}

function appendMessage(role, text) {
  if (!consoleLog) return;

  const entry = document.createElement('div');
  entry.className = `console-entry ${role}`;

  const label = document.createElement('div');
  label.className = 'console-label';
  label.textContent = role === 'user' ? 'User' : 'RICO';

  const message = document.createElement('div');
  message.className = 'console-text';
  message.textContent = text;

  entry.appendChild(label);
  entry.appendChild(message);
  consoleLog.appendChild(entry);
  consoleLog.scrollTop = consoleLog.scrollHeight;
}

function maybeTriggerToolImpulse(metadata) {
  if (!metadata) return;

  if (metadata.tool_call || metadata.tool || metadata.tool_called) {
    setCoreState('tool');
  }
}

async function playAudioUrl(audioUrl) {
  if (!audioUrl || !audioEl) return;

  pendingAudioUrl = audioUrl;
  audioEl.src = audioUrl;
  const waitForEnd = () =>
    new Promise((resolve) => {
      const finalize = () => resolve();
      audioEl.addEventListener('ended', finalize, { once: true });
      audioEl.addEventListener('error', finalize, { once: true });
    });

  try {
    await audioEl.play();
    pendingAudioUrl = null;
  } catch (error) {
    if (error && error.name === 'NotAllowedError' && enableAudioButton) {
      enableAudioButton.classList.remove('hidden');
    } else {
      console.warn('Audio playback failed', error);
    }
    return;
  }

  await waitForEnd();
}

function cancelFollowupLoop() {
  followupSessionId += 1;
  if (followupAbortController) {
    followupAbortController.abort();
    followupAbortController = null;
  }
}

async function requestVoiceTurn({ mode, timeoutMs }) {
  followupAbortController = new AbortController();
  const response = await fetch('/api/voice_ptt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, timeout_ms: timeoutMs }),
    signal: followupAbortController.signal,
  });
  followupAbortController = null;

  if (!response.ok) {
    if (response.status === 422) {
      let message = "Didn't catch that, Sir.";
      try {
        const data = await response.json();
        if (data?.message) {
          message = data.message;
        }
      } catch (error) {
        console.warn('Failed to parse no-speech response', error);
      }
      return { error: message };
    }
    if (response.status === 409) {
      let message = 'Audio playback is active. Please wait, Sir.';
      try {
        const data = await response.json();
        if (data?.detail) {
          message = data.detail;
        }
      } catch (error) {
        console.warn('Failed to parse voice error response', error);
      }
      return { error: message };
    }
    throw new Error(`Voice request failed with status ${response.status}`);
  }

  const data = await response.json();
  return { data };
}

async function handleAssistantResponse(data, { enableFollowup } = {}) {
  if (data.reply) {
    appendMessage('assistant', data.reply);
  }
  maybeTriggerToolImpulse(data.metadata);
  await playAudioUrl(data.audio_url);

  if (!enableFollowup || !data.should_followup) return;

  const sessionId = followupSessionId;
  let attempt = 0;
  let shouldContinue = data.should_followup;
  let timeoutMs = data.followup_timeout_ms;
  let nextMode = 'followup';

  while (shouldContinue && sessionId === followupSessionId) {
    setCoreState('listening');
    let result;
    try {
      result = await requestVoiceTurn({ mode: nextMode, timeoutMs });
    } catch (error) {
      console.error('Voice error', error);
      appendMessage('assistant', 'Audio capture unavailable right now, Sir.');
      return;
    }

    setCoreState('thinking');
    if (sessionId !== followupSessionId) return;
    if (result.error) {
      appendMessage('assistant', result.error);
      return;
    }

    const nextData = result.data;
    if (nextData?.text) {
      appendMessage('user', nextData.text);
    }

    await handleAssistantResponse(nextData);

    if (sessionId !== followupSessionId) return;

    shouldContinue = nextData.should_followup;
    timeoutMs = nextData.followup_timeout_ms;
    nextMode = nextData.replied ? 'followup' : 'second_chance';

    if (!nextData.replied && shouldContinue) {
      attempt += 1;
      if (attempt > 1) {
        return;
      }
    }
  }
}

async function sendMessage(value) {
  setCoreState('thinking');
  promptInput.setAttribute('aria-busy', 'true');
  cancelFollowupLoop();

  appendMessage('user', value);

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: value }),
    });

    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const data = await response.json();
    await handleAssistantResponse(data);
  } catch (error) {
    console.error('Chat error', error);
    appendMessage('assistant', 'Something went wrong, Sir.');
  } finally {
    promptInput.value = '';
    promptInput.removeAttribute('aria-busy');
    setCoreState('idle');
  }
}

// Initialize in idle state.
setCoreState('idle');

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const value = promptInput.value.trim();
  if (!value) return;

  sendMessage(value);
});

// When the input regains focus, ensure the core is calm unless it is already processing.
promptInput.addEventListener('focus', () => {
  if (coreEl.dataset.state !== 'thinking') {
    setCoreState('idle');
  }
});

// Placeholder hooks for microphone lifecycle.
document.addEventListener('rico-voice-start', () => setCoreState('listening'));
document.addEventListener('rico-voice-end', () => setCoreState('idle'));

if (enableAudioButton) {
  enableAudioButton.addEventListener('click', async () => {
    enableAudioButton.classList.add('hidden');

    if (pendingAudioUrl) {
      try {
        audioEl.src = pendingAudioUrl;
        await audioEl.play();
      } catch (error) {
        console.warn('Playback still blocked', error);
      } finally {
        pendingAudioUrl = null;
      }
    }
  });
}

async function handleVoiceInput() {
  if (!micButton || micBusy) return;

  micBusy = true;
  setCoreState('listening');
  cancelFollowupLoop();

  try {
    const result = await requestVoiceTurn({
      mode: 'manual',
      timeoutMs: 20000,
    });
    setCoreState('thinking');

    if (result.error) {
      appendMessage('assistant', result.error);
      return;
    }

    const data = result.data;
    if (data.text) {
      appendMessage('user', data.text);
    }

    await handleAssistantResponse(data, { enableFollowup: true });
  } catch (error) {
    console.error('Voice error', error);
    appendMessage('assistant', 'Audio capture unavailable right now, Sir.');
  } finally {
    micBusy = false;
    setCoreState('idle');
  }
}

micButton?.addEventListener('click', handleVoiceInput);
