(function () {
  const coreEl = document.getElementById('core');
  const canvas = document.getElementById('neuralCanvas');
  if (!coreEl || !canvas) return;

  const ctx = canvas.getContext('2d');
  const nodeCount = Math.floor(110 + Math.random() * 20); // 110-130 nodes
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
  let nextPulse = performance.now() + randomRange(2500, 5000);

  const settings = {
    idle: { pulseSpeed: 0.36, linkOpacity: 0.05 },
    thinking: { pulseSpeed: 0.52, linkOpacity: 0.08 },
    listening: { pulseSpeed: 0.52, linkOpacity: 0.08 },
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
      const swirlDir = Math.random() < 0.5 ? -1 : 1;
      nodes.push({
        x,
        y,
        vx: randomRange(-0.05, 0.05),
        vy: randomRange(-0.05, 0.05),
        flowBias: {
          swirlDir,
          swirlStrength: randomRange(0.0035, 0.0055),
          phase: Math.random() * Math.PI * 2,
          phaseRate: randomRange(0.8, 1.4),
          radialJitter: randomRange(0.0007, 0.0014),
          phaseOffset: Math.random() * Math.PI * 2,
        },
        baseRadius: Math.random() < 0.05 ? randomRange(1.2, 1.6) : randomRange(0.6, 1.2),
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

  function updateNodes(dt) {
    const drift = 0.008;
    nodes.forEach((node) => {
      const dx = node.x - center.x;
      const dy = node.y - center.y;
      const dist = Math.hypot(dx, dy) || 0.0001;
      const nx = dx / dist;
      const ny = dy / dist;

      node.flowBias.phase += dt * node.flowBias.phaseRate;
      const swirlMagnitude = node.flowBias.swirlStrength * (0.9 + 0.25 * Math.sin(node.flowBias.phase));
      const swirlX = -ny * swirlMagnitude * node.flowBias.swirlDir;
      const swirlY = nx * swirlMagnitude * node.flowBias.swirlDir;
      const radialWave = node.flowBias.radialJitter * Math.sin(node.flowBias.phase * 1.35 + node.flowBias.phaseOffset);

      node.vx += swirlX * dt + nx * radialWave * dt;
      node.vy += swirlY * dt + ny * radialWave * dt;
      node.vx += randomRange(-drift, drift) * dt;
      node.vy += randomRange(-drift, drift) * dt;
      node.vx = Math.max(-0.06, Math.min(0.06, node.vx));
      node.vy = Math.max(-0.06, Math.min(0.06, node.vy));

      node.x += node.vx * dt * 60;
      node.y += node.vy * dt * 60;

      const dxAfter = node.x - center.x;
      const dyAfter = node.y - center.y;
      const distAfter = Math.hypot(dxAfter, dyAfter);
      const margin = Math.max(2, radius * 0.02);
      if (distAfter > radius) {
        const nxAfter = dxAfter / distAfter;
        const nyAfter = dyAfter / distAfter;
        const targetDist = Math.max(radius - margin, 0);
        node.x = center.x + nxAfter * targetDist;
        node.y = center.y + nyAfter * targetDist;

        const dot = node.vx * nxAfter + node.vy * nyAfter;
        node.vx -= 2 * dot * nxAfter;
        node.vy -= 2 * dot * nyAfter;

        node.vx *= 0.92;
        node.vy *= 0.92;
      }
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
    const nodeStrength = new Float32Array(nodes.length);
    pulses.forEach((pulse) => {
      const progress = Math.min(1, Math.max(0, (now - pulse.start) / (pulse.end - pulse.start)));
      const eased = Math.sin(progress * Math.PI);
      pulseStrength.set(pulse.key, {
        strength: eased,
        progress,
        phase: pulse.phase,
        length: pulse.length,
      });
      nodeStrength[pulse.a] = Math.max(nodeStrength[pulse.a], eased);
      nodeStrength[pulse.b] = Math.max(nodeStrength[pulse.b], eased);
    });
    return { pulseStrength, nodeStrength };
  }

  function drawLinks(links, now, pulseEffects) {
    const opacityBase = settings[state]?.linkOpacity ?? settings.idle.linkOpacity;
    const lineWidth = 0.45;

    links.forEach((link) => {
      const a = nodes[link.a];
      const b = nodes[link.b];
      const distance = Math.sqrt(link.distSq);
      const fade = Math.max(0, 1 - distance / (Math.min(width, height) * 0.24));
      const pulseEffect = pulseEffects.pulseStrength.get(linkKey(link.a, link.b));
      const pulseFactor = pulseEffect?.strength || 0;
      const alpha = (opacityBase + pulseFactor * 0.26) * fade;
      if (alpha <= 0) return;

      ctx.lineWidth = lineWidth + pulseFactor * 1.05;
      ctx.strokeStyle = `rgba(255, 168, 80, ${alpha.toFixed(3)})`;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();

      if (pulseEffect) {
        const tBase = (pulseEffect.phase + pulseEffect.progress) % 1;
        const segmentFraction = pulseEffect.length;
        const halfLength = segmentFraction * 0.5;
        const startT = Math.max(0, tBase - halfLength);
        const endT = Math.min(1, tBase + halfLength);
        const sparkStrength = 0.35 + pulseFactor * 0.45;

        const gradient = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
        const midIn = startT + (tBase - startT) * 0.45;
        const midOut = endT - (endT - tBase) * 0.45;
        gradient.addColorStop(Math.max(0, startT - 0.05), 'rgba(255, 200, 140, 0)');
        gradient.addColorStop(startT, 'rgba(255, 200, 140, 0)');
        gradient.addColorStop(midIn, `rgba(255, 205, 150, ${(sparkStrength * 0.65).toFixed(3)})`);
        gradient.addColorStop(tBase, `rgba(255, 215, 170, ${sparkStrength.toFixed(3)})`);
        gradient.addColorStop(midOut, `rgba(255, 205, 150, ${(sparkStrength * 0.65).toFixed(3)})`);
        gradient.addColorStop(endT, 'rgba(255, 200, 140, 0)');
        gradient.addColorStop(Math.min(1, endT + 0.05), 'rgba(255, 200, 140, 0)');

        ctx.lineWidth = Math.max(0.65, lineWidth + pulseFactor * 1.2);
        ctx.strokeStyle = gradient;
        ctx.beginPath();
        const sx = a.x + (b.x - a.x) * startT;
        const sy = a.y + (b.y - a.y) * startT;
        const ex = a.x + (b.x - a.x) * endT;
        const ey = a.y + (b.y - a.y) * endT;
        ctx.moveTo(sx, sy);
        ctx.lineTo(ex, ey);
        ctx.stroke();
      }
    });
  }

  function drawNodes(now, pulseEffects) {
    const pulseSpeed = settings[state]?.pulseSpeed ?? settings.idle.pulseSpeed;
    nodes.forEach((node, index) => {
      const basePulse = 0.12 * Math.sin(now * 0.0014 * pulseSpeed + node.pulseOffset) + 1;
      const nodePulse = pulseEffects?.nodeStrength?.[index] || 0;
      const pulseGlow = 1 + nodePulse * 0.4;
      const r = node.baseRadius * basePulse * pulseGlow;
      const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, r * 1.6);
      gradient.addColorStop(0, 'rgba(255, 173, 94, 0.15)');
      gradient.addColorStop(1, 'rgba(255, 140, 50, 0)');
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r * 1.6, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = 'rgba(255, 170, 80, 0.2)';
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fill();

      if (nodePulse > 0) {
        const highlightR = r * 0.6;
        const highlight = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, highlightR);
        highlight.addColorStop(0, `rgba(255, 220, 180, ${(0.18 + nodePulse * 0.18).toFixed(3)})`);
        highlight.addColorStop(1, 'rgba(255, 200, 150, 0)');
        ctx.fillStyle = highlight;
        ctx.beginPath();
        ctx.arc(node.x, node.y, highlightR, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  }

  function updatePulses(now, links) {
    pulses = pulses.filter((pulse) => pulse.end > now);
    if (now < nextPulse || links.length === 0) return;

    const available = [...links];
    let pulseCount = Math.random() < 0.65 ? 1 : 2;
    if (Math.random() < 0.1) pulseCount += 1;
    pulseCount = Math.min(pulseCount, 3, available.length);
    const duration = randomRange(700, 1200);
    for (let i = 0; i < pulseCount && available.length > 0; i++) {
      const targetIndex = Math.floor(Math.random() * available.length);
      const link = available.splice(targetIndex, 1)[0];
      pulses.push({
        key: linkKey(link.a, link.b),
        start: now,
        end: now + duration,
        a: link.a,
        b: link.b,
        phase: Math.random(),
        length: randomRange(0.1, 0.2),
      });
    }

    nextPulse = now + randomRange(2500, 5000);
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
    let dt = Math.min(delta, 100) / 1000;
    if (dt > 0.05) dt = 0.05;
    updateNodes(dt);

    const links = buildLinks();
    updatePulses(now, links);
    const pulseEffects = buildPulseStrength(now);
    drawLinks(links, now, pulseEffects);
    drawNodes(now, pulseEffects);

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
