"use strict";
// Presentation only: all learning state and actions come from the existing app.
// No requests, storage, reward arithmetic, or authentication belong in this module.
window.AscendWorkspace = (() => {
  const root = document.documentElement;
  const make = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  window.AscendArt?.mountBackdrop();
  function companion() {
    const frame = make('div', undefined, 'challenge-art ws-companion');
    frame.setAttribute('aria-hidden', 'true');
    frame.innerHTML = window.AscendArt.companionMarkup();
    return frame;
  }
  function routeCard(title, detail, href, kind) {
    const anchor = make('a', undefined, `ws-route-card ws-route-${kind}`);
    anchor.href = href;
    const mark = make('span', undefined, 'ws-route-icon');
    // icon() is supplied by app.js; these methods only run after it initializes.
    mark.append(icon(kind === 'example' ? 'book' : 'layers'));
    const copy = make('span', undefined, 'ws-route-copy');
    copy.append(make('strong', title), make('span', detail));
    anchor.append(mark, copy, icon('arrow'));
    return anchor;
  }
  function renderToday({overview, levels, account}) {
    const cards = document.getElementById('today-cards');
    if (!cards) return;
    const first = cards.querySelector(':scope > .next-card, :scope > .empty');
    const choices = make('section', undefined, 'ws-practice-choices');
    const heading = make('div', undefined, 'ws-section-heading');
    heading.append(make('h2', 'Make room for curiosity.'));
    const more = make('a', 'Explore Playground →'); more.href = '#playground/quick'; heading.append(more);
    const links = make('nav', undefined, 'ws-route-cards'); links.setAttribute('aria-label', 'Other ways to practice');
    links.append(routeCard('Worked examples', 'Follow the reasoning', '#playground/quick', 'example'), routeCard('Explore Linux labs', 'Local and hosted guides', '#playground/labs', 'lab'));
    choices.append(heading, links);
    if (first) first.after(choices); else cards.prepend(choices);
    const suggestions = cards.querySelector('.today-aside');
    if (suggestions) {
      const label = make('h2', 'Suggested for you', 'ws-suggestions-heading');
      suggestions.prepend(label);
    }
    const greeting = document.querySelector('#today .page-header .eyebrow');
    const username = account?.username;
    if (greeting) greeting.textContent = username ? `YOUR WORKSPACE · ${username}` : 'YOUR WORKSPACE';
    const slot = document.getElementById('ws-active-track');
    if (slot) {
      slot.replaceChildren(); slot.hidden = !overview.mission;
      if (overview.mission) {
        const anchor = make('a'); anchor.href = '#path';
        anchor.append(make('span', 'YOUR ACTIVE TRACK', 'ws-track-caption'), make('strong', overview.mission.title));
        const main = levels.filter(level => level.lane === 'main');
        const current = main.find(level => level.id === overview.next?.level);
        const all = main.flatMap(level => level.nodes);
        const done = all.filter(node => node.status === 'done').length;
        const progress = make('progress'); progress.max = all.length || 1; progress.value = done; progress.setAttribute('aria-label', `${done} of ${all.length} challenges complete`);
        anchor.append(progress, make('small', current ? `Level ${main.indexOf(current) + 1} of ${main.length}` : `${done} of ${all.length} complete`));
        slot.append(anchor);
      }
    }
  }
  function decoratePath() {
    const intro = document.querySelector('#path-content .path-intro');
    if (!intro || intro.querySelector('.ws-path-art')) return;
    const art = companion(); art.classList.add('ws-path-art'); intro.append(art);
  }
  function installSelectionHighlights() {
    const groups = [
      {selector:'.primary-nav', items:':scope > .nav-item', active:'[aria-current="page"]'},
      {selector:'.time-chips', items:':scope > button', active:'[aria-pressed="true"]'},
      {selector:'.playground-tabs', items:':scope > a', active:'[aria-current="page"]'},
      {selector:'#docs-topics', items:'.docs-topic-group > a', active:'[aria-current="page"]'},
      {selector:'.lab-exercises', items:':scope > a', active:'[aria-current="page"]'},
      {selector:'.pg-prediction', items:':scope > button', active:'[aria-pressed="true"]'},
      {selector:'.decision-choices', items:':scope > .decision-choice', active:':has(input[type="radio"]:checked)', cache:group => group.querySelector('input')?.name || ''},
      {selector:'.community-pack-options', items:':scope > [data-pack-id]', active:'[aria-selected="true"]'},
      {selector:'.context-section nav', items:':scope > a', active:'[aria-current="location"]', line:true}
    ];
    const records = new Map(), previous = new Map(), watched = new Set();
    const reduced = matchMedia('(prefers-reduced-motion: reduce)'), forced = matchMedia('(forced-colors: active)');
    let frame = null, snap = true;
    const motion = () => root.dataset.motion !== 'off' && !reduced.matches && !document.hidden;
    const queue = () => { if (frame === null) frame = requestAnimationFrame(sync); };
    const resize = new ResizeObserver(queue);
    const identity = item => item.getAttribute('href') || item.dataset.tab || item.dataset.minutes || item.dataset.packId || item.textContent;
    const place = (marker, box) => {
      marker.style.transform = `translate3d(${box.x}px, ${box.y}px, 0)`;
      marker.style.width = `${box.width}px`; marker.style.height = `${box.height}px`;
    };
    function sync() {
      frame = null;
      const observe = new Set();
      for (const [group, record] of records) {
        if (!group.isConnected) { records.delete(group); record.track.remove(); }
      }
      for (const config of groups) for (const group of document.querySelectorAll(config.selector)) {
        const items = [...group.querySelectorAll(config.items)];
        const cacheKey = config.selector + (config.cache ? `:${config.cache(group)}` : '');
        if (items.length < 2 || forced.matches) {
          group.classList.remove('sliding-selection');
          const record = records.get(group);
          if (record) { if (!record.track.hidden) record.track.hidden = true; record.visible = false; }
          continue;
        }
        observe.add(group); items.forEach(item => observe.add(item));
        let record = records.get(group), fresh = !record || record.track.parentElement !== group;
        if (!record) {
          const track = make('span', undefined, 'selection-track'), marker = make('span', undefined, 'selection-indicator');
          track.setAttribute('aria-hidden', 'true'); track.inert = true; track.append(marker); track.hidden = true;
          record = {track, marker, last:previous.get(cacheKey), visible:false}; records.set(group, record);
        }
        if (getComputedStyle(group).position === 'static') group.style.position = 'relative';
        group.classList.add('sliding-selection');
        if (fresh) group.append(record.track);
        const selected = items.find(item => item.matches(config.active));
        if (!selected || !group.getClientRects().length) {
          if (!record.track.hidden) record.track.hidden = true;
          record.visible = false; continue;
        }
        if (record.track.hidden) record.track.hidden = false;
        const origin = record.track.getBoundingClientRect(), rect = selected.getBoundingClientRect();
        const sx = origin.width / record.track.offsetWidth || 1, sy = origin.height / record.track.offsetHeight || 1;
        const box = {x:(rect.left - origin.left) / sx, y:(rect.top - origin.top) / sy,
          width:config.line ? 2 : rect.width / sx, height:rect.height / sy};
        const key = identity(selected), signature = items.map(identity).join('|'), viewport = `${innerWidth}:${innerHeight}`;
        const last = record.last;
        const changed = !last || ['x', 'y', 'width', 'height'].some(name => Math.abs(last.box[name] - box[name]) > .1);
        if (fresh || !record.visible || snap || changed || last?.key !== key || last?.signature !== signature) {
          const animate = !snap && motion() && last?.signature === signature && last.viewport === viewport
            && (last.key !== key || record.marker.getAnimations().some(animation => animation.playState === 'running'))
            && (record.visible || fresh);
          if (fresh && animate) {
            record.marker.style.transition = 'none'; place(record.marker, last.box);
            record.marker.getBoundingClientRect();
          }
          record.marker.style.transition = animate ? '' : 'none'; place(record.marker, box);
          record.last = {box, key, signature, viewport}; previous.set(cacheKey, record.last);
        }
        record.visible = true;
      }
      for (const node of watched) if (!observe.has(node)) { resize.unobserve(node); watched.delete(node); }
      for (const node of observe) if (!watched.has(node)) { resize.observe(node); watched.add(node); }
      snap = false;
    }
    new MutationObserver(queue).observe(document.body, {childList:true, subtree:true, attributes:true,
      attributeFilter:['aria-current', 'aria-pressed', 'aria-selected', 'hidden', 'open']});
    const reset = () => { snap = true; queue(); };
    new MutationObserver(reset).observe(root, {attributes:true, attributeFilter:['data-motion']});
    reduced.addEventListener('change', reset); forced.addEventListener('change', reset);
    window.addEventListener('resize', reset, {passive:true});
    document.addEventListener('change', event => { if (event.target.closest('.decision-choices')) queue(); }, {passive:true});
    document.addEventListener('visibilitychange', reset);
    document.fonts.ready.then(reset);
    queue();
  }
  installSelectionHighlights();
  return {companion, renderToday, decoratePath};
})();
