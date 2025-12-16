const coreEl = document.getElementById('core');
const promptInput = document.getElementById('prompt');
const form = document.getElementById('core-form');

function setCoreState(nextState) {
  window.coreStateController?.setCoreState(nextState);
}

// Initialize in idle state.
setCoreState('idle');

function simulateToolDetection(text) {
  return /(weather|search)/i.test(text);
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const value = promptInput.value.trim();
  if (!value) return;

  setCoreState('thinking');
  promptInput.setAttribute('aria-busy', 'true');

  if (simulateToolDetection(value)) {
    setTimeout(() => setCoreState('tool'), 200);
  }

  setTimeout(() => {
    promptInput.value = '';
    promptInput.removeAttribute('aria-busy');
    setCoreState('idle');
  }, 1600);
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
