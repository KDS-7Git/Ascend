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
    const toggle = document.getElementById('motion-toggle');
    const label = reduced.matches ? 'Motion reduced by device settings' : paused ? 'Resume motion effects' : 'Pause motion effects';
    toggle.setAttribute('aria-label', label); toggle.title = label;
    toggle.disabled = reduced.matches;
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
      {opacity: .2, transform: 'translateY(8px)', filter: 'blur(3px)'},
      {opacity: 1, transform: 'none', filter: 'blur(0px)'}
    ], 460);
    // Only section entrances; prose is never split into animated characters.
    const sections = screen.id === 'docs'
      ? screen.querySelectorAll('.guide-summary, .docs-topics')
      : screen.querySelectorAll(':scope > :not(.page-header):not([hidden])');
    [...sections].slice(0, 6).forEach((node, index) => animate(node, [
      {opacity: .35, transform: 'translateY(6px)'},
      {opacity: 1, transform: 'none'}
    ], 380, Math.min(index * 45, 135)));
    if (screen.id === 'stats') {
      screen.querySelectorAll('.week rect').forEach((bar, index) => animate(bar, [
        {transform: 'scaleY(.05)'}, {transform: 'scaleY(1)'}
      ], 600, index * 45));
    }
  }
  document.getElementById('motion-toggle').addEventListener('click', () => setPaused(!paused));
  document.getElementById('motion-preference').addEventListener('change', event => setPaused(event.target.value === 'off'));
  reduced.addEventListener('change', sync);
  document.addEventListener('visibilitychange', () => {
    root.classList.toggle('page-inactive', document.hidden);
    if (document.hidden) cancelEntrances();
  });
  // Keep the native cursor; a soft highlight follows it only over the next task.
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  document.addEventListener('pointermove', event => {
    if (!enabled() || !finePointer.matches) return;
    const card = event.target.closest('.next-card');
    if (!card) return;
    let light = card.querySelector('.hover-light');
    if (!light) {
      light = document.createElement('span'); light.className = 'hover-light';
      light.setAttribute('aria-hidden', 'true'); card.append(light);
    }
    const rect = card.getBoundingClientRect();
    light.style.transform = `translate(${event.clientX - rect.left - 130}px, ${event.clientY - rect.top - 130}px)`;
  }, {passive: true});
  sync();
  return {enter};
})();
