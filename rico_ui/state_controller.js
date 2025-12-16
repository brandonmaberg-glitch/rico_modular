(function () {
  const coreEl = document.getElementById('core');
  const stateIndicator = document.getElementById('state-indicator');
  const rootStyle = document.documentElement.style;

  const DEFAULT_TRANSITION_MS = 450;
  const TOOL_IMPULSE_MS = 650;

  const STATE_PRESETS = {
    idle: {
      linkAlphaBase: 0.05,
      pulseOpacityBoost: 0.26,
      pulseEndpointBoost: 0.18,
      pulseIntervalMinMs: 2500,
      pulseIntervalMaxMs: 5000,
      flowBiasStrength: 1,
      nodeSpeedMultiplier: 1,
      css: {
        breathe: 6.4,
        glow: 1,
        ringDrift: 62,
      },
    },
    listening: {
      linkAlphaBase: 0.055,
      pulseOpacityBoost: 0.28,
      pulseEndpointBoost: 0.2,
      pulseIntervalMinMs: 2100,
      pulseIntervalMaxMs: 4200,
      flowBiasStrength: 1.05,
      nodeSpeedMultiplier: 1.05,
      css: {
        breathe: 5.8,
        glow: 1.08,
        ringDrift: 56,
      },
    },
    thinking: {
      linkAlphaBase: 0.065,
      pulseOpacityBoost: 0.32,
      pulseEndpointBoost: 0.22,
      pulseIntervalMinMs: 1800,
      pulseIntervalMaxMs: 3200,
      flowBiasStrength: 1.12,
      nodeSpeedMultiplier: 1.12,
      css: {
        breathe: 5.2,
        glow: 1.16,
        ringDrift: 48,
      },
    },
    tool: {
      linkAlphaBase: 0.07,
      pulseOpacityBoost: 0.38,
      pulseEndpointBoost: 0.26,
      pulseIntervalMinMs: 1400,
      pulseIntervalMaxMs: 2400,
      flowBiasStrength: 1.2,
      nodeSpeedMultiplier: 1.08,
      css: {
        breathe: 4.9,
        glow: 1.2,
        ringDrift: 44,
      },
    },
    speaking: {
      linkAlphaBase: 0.06,
      pulseOpacityBoost: 0.3,
      pulseEndpointBoost: 0.2,
      pulseIntervalMinMs: 2000,
      pulseIntervalMaxMs: 3800,
      flowBiasStrength: 1.06,
      nodeSpeedMultiplier: 1.04,
      css: {
        breathe: 5.6,
        glow: 1.05,
        ringDrift: 54,
      },
    },
  };

  const renderConfig = structuredClone ? structuredClone(STATE_PRESETS.idle) : JSON.parse(JSON.stringify(STATE_PRESETS.idle));

  let currentState = 'idle';
  let previousState = 'idle';
  let transitionStart = performance.now();
  let transitionDuration = DEFAULT_TRANSITION_MS;
  let startConfig = { ...renderConfig, css: { ...renderConfig.css } };
  let targetConfig = { ...STATE_PRESETS.idle, css: { ...STATE_PRESETS.idle.css } };
  let toolReturnTimeout;

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function applyCssVariables(config) {
    rootStyle.setProperty('--core-breathe-duration', config.css.breathe.toFixed(2));
    rootStyle.setProperty('--core-glow-mult', config.css.glow.toFixed(2));
    rootStyle.setProperty('--ring-drift-speed', config.css.ringDrift.toFixed(2));
  }

  function interpolateConfig(t) {
    const numericKeys = [
      'linkAlphaBase',
      'pulseOpacityBoost',
      'pulseEndpointBoost',
      'pulseIntervalMinMs',
      'pulseIntervalMaxMs',
      'flowBiasStrength',
      'nodeSpeedMultiplier',
    ];

    numericKeys.forEach((key) => {
      renderConfig[key] = lerp(startConfig[key], targetConfig[key], t);
    });

    renderConfig.css = renderConfig.css || {};
    renderConfig.css.breathe = lerp(startConfig.css.breathe, targetConfig.css.breathe, t);
    renderConfig.css.glow = lerp(startConfig.css.glow, targetConfig.css.glow, t);
    renderConfig.css.ringDrift = lerp(startConfig.css.ringDrift, targetConfig.css.ringDrift, t);
  }

  function setIndicator(state) {
    if (!stateIndicator) return;
    stateIndicator.textContent = state.charAt(0).toUpperCase() + state.slice(1);
  }

  function setCoreState(nextState) {
    if (!STATE_PRESETS[nextState]) return;

    if (nextState !== 'tool') {
      previousState = nextState;
    } else {
      clearTimeout(toolReturnTimeout);
      toolReturnTimeout = setTimeout(() => {
        setCoreState(previousState);
      }, TOOL_IMPULSE_MS);
    }

    currentState = nextState;
    transitionDuration = nextState === 'tool' ? TOOL_IMPULSE_MS : DEFAULT_TRANSITION_MS;
    transitionStart = performance.now();
    startConfig = { ...renderConfig, css: { ...renderConfig.css } };
    targetConfig = { ...STATE_PRESETS[nextState], css: { ...STATE_PRESETS[nextState].css } };

    if (coreEl) {
      coreEl.dataset.state = nextState === 'tool' ? previousState : nextState;
    }
    setIndicator(nextState);

    if (window.neuralCoreController?.onStateChange) {
      window.neuralCoreController.onStateChange(nextState);
    }
  }

  function tick(now) {
    const t = Math.min(1, (now - transitionStart) / transitionDuration);
    interpolateConfig(t);
    applyCssVariables(renderConfig);
    requestAnimationFrame(tick);
  }

  applyCssVariables(renderConfig);
  setIndicator(currentState);
  requestAnimationFrame(tick);

  window.coreStateController = {
    setCoreState,
    get currentState() {
      return currentState;
    },
    get renderConfig() {
      return renderConfig;
    },
  };
  window.setCoreState = setCoreState;
})();
