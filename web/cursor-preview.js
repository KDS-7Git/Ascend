"use strict";
// Opt-in design preview, pending the owner's feedback. The default stays the grid.
(() => {
  if (new URLSearchParams(location.search).get('cursor') !== 'circuit') return;
  const layer = document.querySelector('.workspace-hover');
  if (!layer) return;
  document.documentElement.dataset.cursorPreview = 'circuit';
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg'); svg.classList.add('cursor-circuit'); svg.setAttribute('aria-hidden', 'true');
  const line = document.createElementNS(ns, 'path');
  const point = document.createElementNS(ns, 'rect'); point.setAttribute('width', 10); point.setAttribute('height', 10);
  svg.append(line, point); layer.append(svg);
  const fine = matchMedia('(hover: hover) and (pointer: fine)'), reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let cells = [], frame = 0, latest, idle, activeLayer = layer;
  const clear = () => { cells = []; svg.classList.remove('is-tracing'); };
  const draw = () => {
    frame = 0;
    if (document.documentElement.dataset.motion === 'off' || reduced.matches || !fine.matches || document.hidden) { clear(); return; }
    const cardLayer = latest.target.closest?.('.next-card')?.querySelector('.hover-light');
    const target = cardLayer || layer;
    if (target !== activeLayer) { clear(); activeLayer = target; target.append(svg); }
    const bounds = activeLayer.getBoundingClientRect();
    const cell = {x: latest.clientX - bounds.left, y: latest.clientY - bounds.top};
    const last = cells.at(-1);
    if (last && Math.hypot(cell.x - last.x, cell.y - last.y) < 12) return;
    if (last && Math.hypot(cell.x - last.x, cell.y - last.y) > 120) cells = [];
    cells.push(cell); cells = cells.slice(-9);
    line.setAttribute('d', cells.map((p, i) => i ? `H${p.x}V${p.y}` : `M${p.x} ${p.y}`).join(''));
    point.setAttribute('x', cell.x - 5); point.setAttribute('y', cell.y - 5);
    svg.classList.add('is-tracing'); clearTimeout(idle); idle = setTimeout(clear, 650);
  };
  document.addEventListener('pointermove', event => { latest = event; if (!frame) frame = requestAnimationFrame(draw); }, {passive: true});
  document.documentElement.addEventListener('pointerleave', clear);
  document.addEventListener('visibilitychange', clear);
  window.addEventListener('blur', clear);
})();
