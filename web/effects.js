"use strict";
// Small, local motion primitives. Content stays readable without this enhancement.
window.AscendMotion = (() => {
  const root = document.documentElement;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const running = new Set();
  const feedbackEvents = new WeakMap();
  let lastPage = null;
  let paused = root.dataset.motion === 'off';
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const pointerProperties = ['--pointer-shadow-x', '--pointer-shadow-y', '--pointer-art-x', '--pointer-art-y', '--pointer-art-angle'];
  let pointerCard = null, pointerSurface = null, pointerFrame = null, pointerSample = null;

  const forcedColors = window.matchMedia('(forced-colors: active)');
  const pageGrid = document.createElement('span');
  pageGrid.className = 'hover-light workspace-hover';
  pageGrid.setAttribute('aria-hidden', 'true');
  document.body.append(pageGrid);
  let gridFrame = null, gridSample = null, cardGrid = null;

  function clearGrid() {
    if (gridFrame !== null) cancelAnimationFrame(gridFrame);
    gridFrame = null; gridSample = null;
    pageGrid.classList.remove('pointer-present');
    cardGrid?.classList.remove('pointer-present'); cardGrid = null;
  }
  function positionGrid(layer, size) {
    const rect = layer.getBoundingClientRect();
    const sx = rect.width / layer.offsetWidth || 1, sy = rect.height / layer.offsetHeight || 1;
    layer.style.setProperty('--pointer-x', `${(gridSample.x - rect.left) / sx}px`);
    layer.style.setProperty('--pointer-y', `${(gridSample.y - rect.top) / sy}px`);
    // Every layer uses the same viewport origin as the fixed paper background.
    layer.style.setProperty('--grid-size-x', `${size / sx}px`);
    layer.style.setProperty('--grid-size-y', `${size / sy}px`);
    layer.style.setProperty('--grid-line-x', `${1 / sx}px`);
    layer.style.setProperty('--grid-line-y', `${1 / sy}px`);
    layer.style.setProperty('--grid-offset-x', `${-rect.left / sx}px`);
    layer.style.setProperty('--grid-offset-y', `${-rect.top / sy}px`);
    layer.style.setProperty('--cell-x', `${(Math.floor(gridSample.x / size) * size - rect.left) / sx}px`);
    layer.style.setProperty('--cell-y', `${(Math.floor(gridSample.y / size) * size - rect.top) / sy}px`);
    layer.classList.add('pointer-present');
  }
  function movingGeometry(surface) {
    for (let node = surface; node && node !== document.body; node = node.parentElement) {
      if (node.getAnimations().some(animation => animation.playState === 'running'
        && Number.isFinite(animation.effect?.getComputedTiming().endTime)
        && animation.effect.getKeyframes().some(frame => frame.transform || frame.translate || frame.rotate))) return true;
    }
    return false;
  }
  function alignPaperGrid(size) {
    const card = document.querySelector('#today-cards>.next-card');
    if (!card?.offsetWidth) return false;
    const rect = card.getBoundingClientRect();
    const sx = rect.width / card.offsetWidth || 1, sy = rect.height / card.offsetHeight || 1;
    card.style.setProperty('--paper-grid-x', `${-rect.left / sx - card.clientLeft}px`);
    card.style.setProperty('--paper-grid-y', `${-rect.top / sy - card.clientTop}px`);
    card.style.setProperty('--paper-grid-size-x', `${size / sx}px`);
    card.style.setProperty('--paper-grid-size-y', `${size / sy}px`);
    card.style.setProperty('--paper-grid-line-x', `${1 / sx}px`);
    card.style.setProperty('--paper-grid-line-y', `${1 / sy}px`);
    return movingGeometry(card);
  }
  function paintGrid() {
    gridFrame = null;
    const size = parseFloat(getComputedStyle(root).getPropertyValue('--workspace-grid-size')) || 28;
    const paperMoving = alignPaperGrid(size);
    if (!gridSample || !enabled() || !finePointer.matches || forcedColors.matches || document.hidden) {
      clearGrid();
      if (paperMoving && !document.hidden) gridFrame = requestAnimationFrame(paintGrid);
      return;
    }
    positionGrid(pageGrid, size);
    const surface = document.elementFromPoint(gridSample.x, gridSample.y)?.closest('.next-card, .ws-route-card, .pg-catalog-card');
    if (cardGrid?.parentElement !== surface) { cardGrid?.classList.remove('pointer-present'); cardGrid = null; }
    if (surface) {
      if (!cardGrid) {
        cardGrid = surface.querySelector(':scope > .hover-light');
        if (!cardGrid) {
          cardGrid = document.createElement('span'); cardGrid.className = 'hover-light';
          cardGrid.setAttribute('aria-hidden', 'true'); surface.append(cardGrid);
        }
      }
      positionGrid(cardGrid, size);
    }
    // Compensate for existing card lifts and page entrances until they settle.
    if (paperMoving || movingGeometry(surface)) gridFrame = requestAnimationFrame(paintGrid);
  }
  function queueGrid() {
    if (gridFrame === null) gridFrame = requestAnimationFrame(paintGrid);
  }

  function resetPointerMotion() {
    if (pointerFrame !== null) cancelAnimationFrame(pointerFrame);
    pointerFrame = null;
    if (pointerCard) {
      delete pointerCard.dataset.pointerMotion;
      pointerProperties.forEach(property => pointerCard.style.removeProperty(property));
    }
    pointerCard = pointerSurface = pointerSample = null;
  }

  function enabled() { return !paused && !reduced.matches; }
  function cancelEntrances() {
    clearGrid();
    resetPointerMotion();
    running.forEach(animation => animation.cancel());
    running.clear();
  }
  function sync() {
    root.dataset.motion = enabled() ? 'calm' : 'off';
    const select = document.getElementById('motion-preference');
    select.value = paused ? 'off' : 'calm';
    const help = select.closest('.motion-preference')?.querySelector('.field-help');
    if (help) help.textContent = reduced.matches ? 'Your device requests reduced motion. Effects stay still while that preference is enabled.' : paused ? 'Motion is off. Choose On for grid highlights and mouse interactions, page transitions, card effects and reward celebrations.' : 'Motion is on: grid highlights and mouse interactions, page transitions, card effects and reward celebrations. Effects pause when this tab is hidden.';
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
    if (screen.id === 'today') {
      const landscape = document.querySelector('.ws-backdrop');
      animate(landscape, [{opacity: 0, transform: 'translateY(18px)'}, {opacity: 1, transform: 'none'}], 1100);
    }
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
  function feedback(node, kind) {
    if (!node || !enabled() || document.hidden) return;
    const last = feedbackEvents.get(node), now = performance.now();
    if (last?.kind === kind && now - last.at < 1000) return;
    feedbackEvents.set(node, {kind, at: now});
    if (kind.startsWith('reward-')) {
      // Answer, challenge and milestone scenes use the same lifecycle controls.
      // The saved explanation and Continue action never wait for the vignette.
      const milestone = kind === 'reward-milestone';
      const scene = node.querySelector('.reward-visual');
      animate(scene, [{opacity: .4, transform: 'scale(.8)'}, {opacity: 1, transform: 'scale(1.08)', offset: .55}, {opacity: 1, transform: 'none'}], milestone ? 700 : 450);
      animate(node.querySelector('.feedback-mark-stroke'), [{strokeDasharray: '1', strokeDashoffset: '1'}, {strokeDasharray: '1', strokeDashoffset: '0'}], 420, 60);
      animate(node.querySelector('.reward-companion'), [
        {transform: 'translateY(0)'}, {transform: `translateY(${milestone ? -11 : -6}px) rotate(-4deg)`, offset: .28},
        {transform: 'translateY(0) rotate(3deg)', offset: .58}, {transform: 'none'}
      ], milestone ? 1150 : 820, 80);
      animate(node.querySelector('.reward-flag'), [{transform: 'rotate(-14deg)'}, {transform: 'rotate(10deg)', offset: .35}, {transform: 'rotate(-5deg)', offset: .7}, {transform: 'none'}], milestone ? 1150 : 750, 160);
      animate(node.querySelector('.reward-medal'), [{transform: 'translateY(12px) rotate(-12deg)', opacity: .2}, {transform: 'translateY(-3px) rotate(4deg)', opacity: 1, offset: .65}, {transform: 'none', opacity: 1}], 850, 100);
      node.querySelectorAll('.reward-star').forEach((star, index) => animate(star, [
        {opacity: 0, transform: 'scale(.2) rotate(-30deg)'},
        {opacity: 1, transform: 'scale(1.35) rotate(10deg)', offset: .5},
        {opacity: 1, transform: 'none'}
      ], milestone ? 900 : 600, index * 100 + 120));
      animate(node.querySelector('.reward-xp'), [{opacity: .35, transform: 'translateY(6px)'}, {opacity: 1, transform: 'none'}], 400, 180);
      animate(node.querySelector('.reward-practice'), [{opacity: .35, transform: 'translateY(6px)'}, {opacity: 1, transform: 'none'}], 400, 100);
      return;
    }
    const celebration = kind === 'complete' || kind === 'streak';
    animate(node, celebration ? [
      {opacity: .35, transform: 'translateY(14px) scale(.96)'},
      {opacity: 1, transform: 'translateY(-3px) scale(1.015)', offset: .65},
      {opacity: 1, transform: 'none'}
    ] : [{opacity: .45, transform: 'translateY(5px)'}, {opacity: 1, transform: 'none'}], celebration ? 620 : 300);
    if (kind === 'complete') {
      const mark = node.querySelector('.completion-mark');
      animate(mark, [{transform: 'rotate(-35deg) scale(.3)'}, {transform: 'rotate(8deg) scale(1.13)', offset: .7}, {transform: 'none'}], 720, 80);
    }
    const glyph = node.querySelector('.feedback-mark-stroke');
    animate(glyph, [{strokeDasharray: '1', strokeDashoffset: '1'}, {strokeDasharray: '1', strokeDashoffset: '0'}], 420, 110);
    const ring = node.querySelector('.feedback-mark');
    animate(ring, [{transform: 'scale(.75)'}, {transform: 'scale(1.12)', offset: .6}, {transform: 'scale(1)'}], 480);
    if (celebration) {
      // A brief, local geometric burst. No full-screen confetti or repeating reward.
      const origin = node.querySelector('.completion-mark, .feedback-mark, .icon');
      if (origin) {
        const bounds = node.getBoundingClientRect(), point = origin.getBoundingClientRect();
        if (getComputedStyle(node).position === 'static') node.style.position = 'relative';
        for (let i = 0; i < 6; i++) {
          const spark = document.createElement('span'); spark.className = 'feedback-spark'; spark.setAttribute('aria-hidden', 'true');
          spark.style.left = `${point.left - bounds.left + point.width / 2}px`;
          spark.style.top = `${point.top - bounds.top + point.height / 2}px`;
          node.append(spark);
          const angle = i * Math.PI / 3, distance = 34;
          animate(spark, [
            {opacity: 0, transform: 'translate(-50%, -50%) scale(0)'},
            {opacity: .85, offset: .2},
            {opacity: 0, transform: `translate(${Math.cos(angle) * distance}px, ${Math.sin(angle) * distance}px) rotate(${i * 60}deg) scale(.4)`}
          ], 680, 80);
          setTimeout(() => spark.remove(), 800);
        }
      }
    }
  }
  document.getElementById('motion-preference').addEventListener('change', event => setPaused(event.target.value === 'off'));
  reduced.addEventListener('change', sync);
  document.addEventListener('visibilitychange', () => {
    root.classList.toggle('page-inactive', document.hidden);
    if (document.hidden) cancelEntrances();
  });
  document.addEventListener('pointermove', event => {
    if (!enabled() || !finePointer.matches || forcedColors.matches || document.hidden || event.pointerType !== 'mouse') { clearGrid(); return; }
    gridSample = {x:event.clientX, y:event.clientY}; queueGrid();
  }, {passive:true});
  document.addEventListener('pointerdown', queueGrid, {passive:true});
  document.addEventListener('pointerup', queueGrid, {passive:true});
  document.addEventListener('scroll', queueGrid, {capture:true, passive:true});
  document.addEventListener('pointercancel', clearGrid, {passive:true});
  window.addEventListener('resize', queueGrid);
  window.addEventListener('blur', clearGrid);
  root.addEventListener('pointerleave', clearGrid);
  finePointer.addEventListener('change', clearGrid);
  forcedColors.addEventListener('change', () => { if (forcedColors.matches) clearGrid(); else queueGrid(); });
  window.addEventListener('focus', queueGrid);
  new MutationObserver(queueGrid).observe(document.getElementById('main'), {childList:true, subtree:true});
  // Mouse movement shifts hard shadows and decorative art. Text and buttons
  // keep their hover positions; the native cursor stays available.
  document.addEventListener('pointermove', event => {
    if (!enabled() || !finePointer.matches || document.hidden || event.pointerType !== 'mouse' || event.buttons) {
      resetPointerMotion(); return;
    }
    const surface = event.target.closest?.('.next-card, .ws-route-card, .pg-catalog-card, .level-header');
    if (!surface) { resetPointerMotion(); return; }
    const card = surface.matches('.level-header') ? surface.parentElement : surface;
    if (card !== pointerCard) resetPointerMotion();
    pointerCard = card; pointerSurface = surface;
    pointerSample = {x:event.clientX, y:event.clientY};
    if (pointerFrame !== null) return;
    pointerFrame = requestAnimationFrame(() => {
      pointerFrame = null;
      if (!pointerCard?.isConnected || !enabled() || document.hidden) { resetPointerMotion(); return; }
      const bounds = pointerSurface.getBoundingClientRect();
      const unit = value => Math.max(-1, Math.min(1, value));
      const x = unit((pointerSample.x - bounds.left) / Math.max(1, bounds.width) * 2 - 1);
      const y = unit((pointerSample.y - bounds.top) / Math.max(1, bounds.height) * 2 - 1);
      pointerCard.dataset.pointerMotion = 'true';
      pointerCard.style.setProperty('--pointer-shadow-x', `${(8 - x * 4).toFixed(1)}px`);
      pointerCard.style.setProperty('--pointer-shadow-y', `${(8 - y * 4).toFixed(1)}px`);
      pointerCard.style.setProperty('--pointer-art-x', `${(x * 5).toFixed(1)}px`);
      pointerCard.style.setProperty('--pointer-art-y', `${(y * 4).toFixed(1)}px`);
      pointerCard.style.setProperty('--pointer-art-angle', `${(x * 3).toFixed(1)}deg`);
    });
  }, {passive:true});
  document.addEventListener('pointerout', event => {
    if (pointerSurface && !pointerSurface.contains(event.relatedTarget)) resetPointerMotion();
  }, {passive:true});
  document.addEventListener('pointerdown', resetPointerMotion, {passive:true});
  document.addEventListener('scroll', resetPointerMotion, {capture:true, passive:true});
  document.documentElement.addEventListener('pointerleave', resetPointerMotion);
  finePointer.addEventListener('change', resetPointerMotion);
  sync();
  document.querySelector('.ambient-scene').hidden = false;
  return {enter, leave, feedback};
})();
