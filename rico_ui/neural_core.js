(function () {
  const coreEl = document.getElementById('core');
  const canvas = document.getElementById('neuralCanvas');
  if (!coreEl || !canvas) return;

  const ctx = canvas.getContext('2d');
  const nodeCount = Math.floor(120 + Math.random() * 40); // 120-160 nodes
  const nodes = [];
  let width = 0;
  let height = 0;
  let radius = 0;
  let dpr = window.devicePixelRatio || 1;
  let lastFrame = 0;
  let visible = !document.hidden;
  let state = 'idle';
  let center = { x: 0, y: 0 };
  let pulses = [];
  let nextPulse = performance.now() + randomRange(800, 2500);

  const settings = {
    idle: { pulseSpeed: 0.36, linkOpacity: 0.06 },
    thinking: { pulseSpeed: 0.52, linkOpacity: 0.1 },
    listening: { pulseSpeed: 0.52, linkOpacity: 0.1 },
  };

  function randomRange(min, max) {
    return Math.random() * (max - min) + min;
  }

  function initializeNodes() {
    nodes.length = 0;
    for (let i = 0; i < nodeCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const r = Math.sqrt(Math.random()) * radius;
      const x = center.x + Math.cos(angle) * r;
      const y = center.y + Math.sin(angle) * r;
      nodes.push({
        x,
        y,
        vx: randomRange(-0.05, 0.05),
        vy: randomRange(-0.05, 0.05),
        baseRadius: Math.random() < 0.08 ? randomRange(1.3, 1.8) : randomRange(0.7, 1.4),
        pulseOffset: Math.random() * Math.PI * 2,
      });
    }
  }

  function resize() {
    const rect = coreEl.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    radius = Math.min(width, height) / 2;
    center = { x: width / 2, y: height / 2 };

    dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    initializeNodes();
  }

  function gentlyRecenter(node) {
    const dx = node.x - center.x;
    const dy = node.y - center.y;
    const dist = Math.hypot(dx, dy);
    if (dist > radius) {
      const pull = (dist - radius) * 0.02;
      node.vx -= (dx / dist) * pull;
      node.vy -= (dy / dist) * pull;
    }
  }

  function updateNodes(dt) {
    const drift = 0.015;
    nodes.forEach((node) => {
      node.vx += randomRange(-drift, drift) * dt;
      node.vy += randomRange(-drift, drift) * dt;
      node.vx = Math.max(-0.08, Math.min(0.08, node.vx));
      node.vy = Math.max(-0.08, Math.min(0.08, node.vy));

      node.x += node.vx * dt * 60;
      node.y += node.vy * dt * 60;
      gentlyRecenter(node);
    });
  }

  function buildLinks() {
    const maxDistance = Math.min(width, height) * 0.22;
    const maxDistanceSq = maxDistance * maxDistance;
    const nodeLinks = new Array(nodes.length).fill(0);
    const links = [];

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (links.length >= 140) return links;
        if (nodeLinks[i] >= 3 || nodeLinks[j] >= 3) continue;
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const distSq = dx * dx + dy * dy;
        if (distSq > maxDistanceSq) continue;

        links.push({ a: i, b: j, distSq });
        nodeLinks[i] += 1;
        nodeLinks[j] += 1;
      }
    }

    return links;
  }

  function linkKey(a, b) {
    return a < b ? `${a}-${b}` : `${b}-${a}`;
  }

  function buildPulseStrength(now) {
    const pulseStrength = new Map();
    pulses.forEach((pulse) => {
      const progress = Math.min(1, Math.max(0, (now - pulse.start) / (pulse.end - pulse.start)));
      const eased = Math.sin(progress * Math.PI);
      pulseStrength.set(pulse.key, eased);
    });
    return pulseStrength;
  }

  function drawLinks(links, now, pulseStrength) {
    const opacityBase = settings[state]?.linkOpacity ?? settings.idle.linkOpacity;
    const lineWidth = 0.5;

    links.forEach((link) => {
      const a = nodes[link.a];
      const b = nodes[link.b];
      const distance = Math.sqrt(link.distSq);
      const fade = Math.max(0, 1 - distance / (Math.min(width, height) * 0.24));
      const pulseFactor = pulseStrength.get(linkKey(link.a, link.b)) || 0;
      const alpha = (opacityBase + pulseFactor * 0.16) * fade;
      if (alpha <= 0) return;

      ctx.lineWidth = lineWidth + pulseFactor * 0.5;
      ctx.strokeStyle = `rgba(255, 168, 80, ${alpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    });
  }

  function drawNodes(now) {
    const pulseSpeed = settings[state]?.pulseSpeed ?? settings.idle.pulseSpeed;
    nodes.forEach((node) => {
      const pulse = 0.12 * Math.sin(now * 0.0014 * pulseSpeed + node.pulseOffset) + 1;
      const r = node.baseRadius * pulse;
      const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r * 1.6);
      gradient.addColorStop(0, 'rgba(255, 173, 94, 0.18)');
      gradient.addColorStop(1, 'rgba(255, 140, 50, 0)');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r * 1.6, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = 'rgba(255, 170, 80, 0.2)';
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function updatePulses(now, links) {
    pulses = pulses.filter((pulse) => pulse.end > now);
    if (now < nextPulse || links.length === 0) return;

    const available = [...links];
    const pulseCount = Math.min(3, Math.max(1, Math.floor(Math.random() * 3) + 1, available.length));
    const duration = randomRange(250, 500);
    for (let i = 0; i < pulseCount && available.length > 0; i++) {
      const targetIndex = Math.floor(Math.random() * available.length);
      const link = available.splice(targetIndex, 1)[0];
      pulses.push({
        key: linkKey(link.a, link.b),
        start: now,
        end: now + duration,
      });
    }

    nextPulse = now + randomRange(800, 2500);
  }

  function render(now) {
    if (!visible) {
      lastFrame = now;
      requestAnimationFrame(render);
      return;
    }
    const delta = now - lastFrame;
    if (delta < 1000 / 30) {
      requestAnimationFrame(render);
      return;
    }
    lastFrame = now;

    ctx.clearRect(0, 0, width, height);
    const dt = Math.min(delta, 100) / 1000;
    updateNodes(dt);

    const links = buildLinks();
    updatePulses(now, links);
    const pulseStrength = buildPulseStrength(now);
    drawLinks(links, now, pulseStrength);
    drawNodes(now);

    requestAnimationFrame(render);
  }

  function handleVisibility() {
    visible = !document.hidden;
  }

  function setState(nextState) {
    state = nextState;
  }

  resize();
  window.addEventListener('resize', resize);
  document.addEventListener('visibilitychange', handleVisibility);
  requestAnimationFrame((time) => {
    lastFrame = time;
    render(time);
  });

  window.neuralCoreController = { setState };
})();
