"use strict";
// Small, local motion primitives. Content stays readable without this enhancement.
window.AscendMotion = (() => {
  const root = document.documentElement;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const running = new Set();
  let lastPage = null;
  let paused = root.dataset.motion === 'off';

  function enabled() { return !paused && !reduced.matches; }
  function cancelEntrances() {
    running.forEach(animation => animation.cancel());
    running.clear();
  }
  function sync() {
    root.dataset.motion = enabled() ? 'calm' : 'off';
    const select = document.getElementById('motion-preference');
    select.value = paused ? 'off' : 'calm';
    if (!enabled()) cancelEntrances();
  }
  function setPaused(value) {
    paused = value;
    try { localStorage.setItem('ascend-motion', paused ? 'off' : 'calm'); } catch { /* This session still honors the choice. */ }
    sync();
  }
  function animate(node, frames, duration, delay = 0) {
    if (!node?.animate || !enabled()) return;
    const animation = node.animate(frames, {duration, delay, easing: 'cubic-bezier(.22, 1, .36, 1)', fill: 'backwards'});
    running.add(animation);
    animation.finished.then(() => running.delete(animation), () => running.delete(animation));
  }
  function enter(screen, key) {
    root.dataset.view = screen.id;
    if (key === lastPage) return;
    lastPage = key;
    cancelEntrances();
    if (!enabled()) return;
    const title = screen.querySelector('h1');
    animate(title, [
      {opacity: 0, transform: 'translateY(18px)', clipPath: 'inset(0 0 100% 0)'},
      {opacity: 1, transform: 'none', clipPath: 'inset(0 0 0% 0)'}
    ], 480);
    // Only section entrances; prose is never split into animated characters.
    const sections = screen.id === 'docs'
      ? screen.querySelectorAll('.guide-summary, .docs-topics')
      : screen.querySelectorAll(':scope > :not(.page-header):not([hidden])');
    [...sections].slice(0, 6).forEach((node, index) => animate(node, [
      {opacity: 0, transform: 'translateY(16px) scale(.985)'},
      {opacity: 1, transform: 'none'}
    ], 440, Math.min(index * 65 + 50, 245)));
    const details = screen.querySelectorAll('.pack-item, .level-section, .settings, .case-choice');
    [...details].slice(0, 7).forEach((node, index) => animate(node, [
      {opacity: 0, transform: 'translateX(12px)'}, {opacity: 1, transform: 'none'}
    ], 320, index * 45 + 100));
    if (screen.id === 'stats') {
      screen.querySelectorAll('.week rect').forEach((bar, index) => animate(bar, [
        {transform: 'scaleY(.05)'}, {transform: 'scaleY(1)'}
      ], 600, index * 45));
    }
  }
  async function leave(screen) {
    if (!enabled() || !screen?.animate) return;
    cancelEntrances();
    const animation = screen.animate([{opacity: 1}, {opacity: 0, transform: 'translateY(-6px)'}], {duration: 100, easing: 'ease-in'});
    running.add(animation);
    try { await animation.finished; } catch { /* Interrupted navigation. */ }
    running.delete(animation);
  }
  document.getElementById('motion-preference').addEventListener('change', event => setPaused(event.target.value === 'off'));
  reduced.addEventListener('change', sync);
  document.addEventListener('visibilitychange', () => {
    root.classList.toggle('page-inactive', document.hidden);
    if (document.hidden) cancelEntrances();
  });
  // Keep the native cursor; reveal a fixed grid and emphasize its nearest cell.
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const pageGrid = document.createElement('span');
  pageGrid.className = 'hover-light workspace-hover'; pageGrid.setAttribute('aria-hidden', 'true');
  document.body.append(pageGrid);
  function positionGrid(layer, event, container) {
    const rect = container.getBoundingClientRect();
    const x = event.clientX - rect.left - container.clientLeft;
    const y = event.clientY - rect.top - container.clientTop;
    layer.style.setProperty('--pointer-x', `${x}px`);
    layer.style.setProperty('--pointer-y', `${y}px`);
    layer.style.setProperty('--cell-x', `${Math.floor(x / 24) * 24}px`);
    layer.style.setProperty('--cell-y', `${Math.floor(y / 24) * 24}px`);
  }
  document.addEventListener('pointermove', event => {
    if (!enabled() || !finePointer.matches) return;
    positionGrid(pageGrid, event, pageGrid);
    pageGrid.classList.add('pointer-present');
    const card = event.target.closest('.next-card');
    if (!card) return;
    let light = card.querySelector('.hover-light');
    if (!light) {
      light = document.createElement('span'); light.className = 'hover-light';
      light.setAttribute('aria-hidden', 'true'); card.append(light);
    }
    positionGrid(light, event, card);
  }, {passive: true});
  document.documentElement.addEventListener('pointerleave', () => pageGrid.classList.remove('pointer-present'));
  sync();
  document.querySelector('.ambient-scene').hidden = false;
  return {enter, leave};
})();
