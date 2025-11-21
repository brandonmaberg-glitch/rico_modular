const wsStatus = document.getElementById('ws-status');
const wsDot = document.getElementById('ws-dot');
const ring = document.getElementById('ring');
const ringCore = ring.querySelector('.ring-core');
const consoleEl = document.getElementById('console');
const resultsEl = document.getElementById('results');
const imageGridEl = document.getElementById('image-grid');
const modalEl = document.getElementById('image-modal');
const modalImage = document.getElementById('modal-image');
const modalClose = document.getElementById('image-modal-close');
const providerEl = document.getElementById('provider');
const skillIndicator = document.getElementById('skill-indicator');
const listeningIndicator = document.getElementById('listening-indicator');

let socket;
let reconnectTimeout;
let speakingActive = false;

function setStatus(text, ok = false) {
  wsStatus.textContent = text;
  wsDot.style.background = ok ? '#6ee6ff' : '#ff8a6b';
  wsDot.style.boxShadow = ok
    ? '0 0 12px rgba(110,230,255,0.8)'
    : '0 0 12px rgba(255,138,107,0.8)';
}

function setRingState(state) {
  ring.classList.remove('listening', 'thinking', 'speaking');
  ring.classList.remove('fallback');
  if (state) {
    ring.classList.add(state);
  }
}

function addConsoleEntry(role, text, meta = '') {
  const entry = document.createElement('div');
  entry.className = 'console-entry';
  const metaEl = document.createElement('div');
  metaEl.className = 'meta';
  metaEl.textContent = `${role}${meta ? ' · ' + meta : ''}`;
  const textEl = document.createElement('div');
  textEl.className = 'text';
  textEl.textContent = text;
  entry.appendChild(metaEl);
  entry.appendChild(textEl);
  consoleEl.appendChild(entry);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

function addChartCard(chartData, title) {
  const card = document.createElement('div');
  card.className = 'result-card';
  const titleEl = document.createElement('div');
  titleEl.className = 'title';
  titleEl.textContent = title || 'Chart';
  const canvas = document.createElement('canvas');
  card.appendChild(titleEl);
  card.appendChild(canvas);
  resultsEl.prepend(card);
  try {
    new Chart(canvas.getContext('2d'), chartData); // eslint-disable-line no-new
  } catch (err) {
    titleEl.textContent = 'Chart unavailable';
    const error = document.createElement('div');
    error.className = 'snippet';
    error.textContent = err?.message || 'Invalid chart payload';
    card.appendChild(error);
  }
}

function addTextCard(snippet, title = 'Result') {
  const card = document.createElement('div');
  card.className = 'result-card';
  const titleEl = document.createElement('div');
  titleEl.className = 'title';
  titleEl.textContent = title;
  const textEl = document.createElement('div');
  textEl.className = 'snippet';
  textEl.textContent = snippet;
  card.appendChild(titleEl);
  card.appendChild(textEl);
  resultsEl.prepend(card);
}

function addWebPreviewCard(data) {
  const card = document.createElement('div');
  card.className = 'preview-card';

  if (data.image) {
    const img = document.createElement('img');
    img.src = data.image;
    img.alt = data.title || 'Preview image';
    card.appendChild(img);
  } else {
    const placeholder = document.createElement('div');
    placeholder.className = 'widget';
    placeholder.textContent = 'No preview image';
    card.appendChild(placeholder);
  }

  const content = document.createElement('div');
  const titleEl = document.createElement('div');
  titleEl.className = 'title';
  titleEl.textContent = data.title || 'Web preview';
  const snippetEl = document.createElement('div');
  snippetEl.className = 'snippet';
  snippetEl.textContent = data.snippet || '';
  const sourceEl = document.createElement('a');
  sourceEl.href = data.url || '#';
  sourceEl.textContent = data.url || 'Source';
  sourceEl.target = '_blank';
  sourceEl.rel = 'noreferrer';
  sourceEl.className = 'source';

  content.appendChild(titleEl);
  content.appendChild(snippetEl);
  content.appendChild(sourceEl);
  card.appendChild(content);
  resultsEl.prepend(card);
}

function renderImageGrid(images = []) {
  imageGridEl.innerHTML = '';
  images.forEach((url, idx) => {
    const thumb = document.createElement('div');
    thumb.className = 'image-thumb';
    const img = document.createElement('img');
    img.src = url;
    img.alt = `Result ${idx + 1}`;
    thumb.appendChild(img);
    thumb.addEventListener('click', () => openModal(url));
    imageGridEl.appendChild(thumb);
  });
}

function openModal(url) {
  modalImage.src = url;
  modalEl.classList.add('open');
}

function closeModal() {
  modalEl.classList.remove('open');
  modalImage.src = '';
}

modalClose.addEventListener('click', closeModal);
modalEl.addEventListener('click', (e) => {
  if (e.target === modalEl) closeModal();
});

function setSpeakingAnimation(active) {
  speakingActive = active;
  ring.style.setProperty('--audio-level', 0);
  if (active) {
    setRingState('speaking');
    ring.classList.add('fallback');
    listeningIndicator.textContent = 'Speaking now';
  } else {
    setRingState('');
    ring.classList.remove('fallback');
    listeningIndicator.textContent = 'Listening: idle';
    ringCore.style.transform = '';
  }
}

function updateAudioLevel(level) {
  const clamped = Math.max(0, Math.min(level, 1));
  ring.classList.remove('fallback');
  ring.classList.add('speaking');
  ring.style.setProperty('--audio-level', clamped);
  ringCore.style.transform = `scale(${1 + clamped * 0.25})`;
}

function handleEvent(data) {
  const type = data.type;
  switch (type) {
    case 'transcription':
      setRingState('listening');
      listeningIndicator.textContent = 'Listening: captured input';
      addConsoleEntry('User', data.text || '');
      break;
    case 'speech':
      addConsoleEntry('RICO', data.text || '');
      break;
    case 'thinking':
      setRingState(data.intensity > 0 ? 'thinking' : '');
      ring.style.boxShadow = `0 0 ${18 + (data.intensity || 0) * 35}px rgba(110, 230, 255, 0.5)`;
      break;
    case 'image':
      addTextCard('Received legacy image event', 'Notice');
      break;
    case 'chart':
      addChartCard(data.data, data.title);
      break;
    case 'skill':
      skillIndicator.textContent = `Skill: ${data.skill}`;
      break;
    case 'provider':
      providerEl.textContent = `Voice: ${data.provider}`;
      addTextCard(`Voice provider switched to ${data.provider}.`, 'Voice update');
      break;
    case 'speaking_start':
      setSpeakingAnimation(true);
      break;
    case 'speaking_end':
      setSpeakingAnimation(false);
      break;
    case 'audio_level':
      if (speakingActive) updateAudioLevel(data.value ?? 0);
      break;
    case 'listening':
      listeningIndicator.textContent = data.active ? 'Listening: awaiting input' : 'Listening: idle';
      setRingState(data.active ? 'listening' : '');
      break;
    case 'state':
      listeningIndicator.textContent = `State: ${data.state}`;
      setRingState(data.state);
      break;
    case 'image_results':
      renderImageGrid(data.images || []);
      addTextCard(`Showing ${data.images?.length || 0} image result(s).`, 'Image search');
      break;
    case 'web_preview':
      addWebPreviewCard(data);
      break;
    default:
      addTextCard(JSON.stringify(data), 'System event');
  }
}

function connect() {
  const wsUrl = 'ws://localhost:8765';
  socket = new WebSocket(wsUrl);
  socket.onopen = () => {
    setStatus('Connected to RICO', true);
    addConsoleEntry('System', 'UI link established.');
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
  };
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleEvent(data);
    } catch (err) {
      addTextCard('Malformed event from backend', 'Error');
    }
  };
  socket.onclose = () => {
    setStatus('Reconnecting...', false);
    setRingState('');
    reconnectTimeout = setTimeout(connect, 1500);
  };
  socket.onerror = () => {
    setStatus('Connection error', false);
  };
}

connect();

// Seed the console with a welcome entry for static loads
addConsoleEntry('RICO', 'Awaiting your command, Sir.');
