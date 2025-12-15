const coreEl = document.getElementById('core');
const stateIndicator = document.getElementById('state-indicator');
const promptInput = document.getElementById('prompt');
const form = document.getElementById('core-form');

/**
 * Centralized state setter for the core pulse.
 * Available states: `idle`, `thinking`, `listening`.
 */
function setCoreState(nextState) {
  coreEl.dataset.state = nextState;
  stateIndicator.textContent = nextState.charAt(0).toUpperCase() + nextState.slice(1);
  if (window.neuralCoreController?.setState) {
    window.neuralCoreController.setState(nextState);
  }
}

// Start in idle mode with a slow breathing pulse.
setCoreState('idle');

// Mock thinking cycle: when the user submits a prompt, speed up the pulse
// to signal processing, then return to idle after a delay.
form.addEventListener('submit', (event) => {
  event.preventDefault();
  const value = promptInput.value.trim();
  if (!value) return;

  setCoreState('thinking');
  promptInput.setAttribute('aria-busy', 'true');

  // Simulated tool response placeholder
  setTimeout(() => {
    promptInput.value = '';
    promptInput.removeAttribute('aria-busy');
    setCoreState('idle');
  }, 1600);
});

// When the input regains focus, ensure the core is calm unless it is thinking.
promptInput.addEventListener('focus', () => {
  if (coreEl.dataset.state !== 'thinking') {
    setCoreState('idle');
  }
});
