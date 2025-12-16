const coreEl = document.getElementById('core');
const promptInput = document.getElementById('prompt');
const form = document.getElementById('core-form');
const consoleLog = document.getElementById('console-log');

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

async function sendMessage(value) {
  setCoreState('thinking');
  promptInput.setAttribute('aria-busy', 'true');

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
    appendMessage('assistant', data.reply || '');
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
