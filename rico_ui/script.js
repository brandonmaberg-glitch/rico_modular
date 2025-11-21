const wsStatus = document.getElementById('ws-status');
const wsDot = document.getElementById('ws-dot');
const ring = document.getElementById('ring');
const consoleEl = document.getElementById('console');
const resultsEl = document.getElementById('results');
const providerEl = document.getElementById('provider');
const skillIndicator = document.getElementById('skill-indicator');
const listeningIndicator = document.getElementById('listening-indicator');

let socket;
let reconnectTimeout;

function setStatus(text, ok = false) {
  wsStatus.textContent = text;
  wsDot.style.background = ok ? '#6ee6ff' : '#ff8a6b';
  wsDot.style.boxShadow = ok
    ? '0 0 12px rgba(110,230,255,0.8)'
    : '0 0 12px rgba(255,138,107,0.8)';
}

function setRingState(state) {
  ring.classList.remove('listening', 'thinking', 'speaking');
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

function addImageCard(url, caption) {
  const card = document.createElement('div');
  card.className = 'result-card';
  const title = document.createElement('div');
  title.className = 'title';
  title.textContent = caption || 'Image result';
  const img = document.createElement('img');
  img.src = url;
  img.alt = caption || 'Result image';
  card.appendChild(title);
  card.appendChild(img);
  resultsEl.prepend(card);
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
      setRingState('speaking');
      break;
    case 'thinking':
      setRingState(data.intensity > 0 ? 'thinking' : '');
      ring.style.boxShadow = `0 0 ${18 + (data.intensity || 0) * 35}px rgba(110, 230, 255, 0.5)`;
      break;
    case 'image':
      addImageCard(data.url, data.caption);
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
    case 'speaking':
      setRingState(data.active ? 'speaking' : '');
      listeningIndicator.textContent = data.active ? 'Speaking now' : 'Listening: idle';
      break;
    case 'listening':
      listeningIndicator.textContent = data.active ? 'Listening: awaiting input' : 'Listening: idle';
      setRingState(data.active ? 'listening' : '');
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
