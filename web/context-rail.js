"use strict";
// Supporting navigation and real progress use the room beside the working column.
// No extra data requests, placeholder metrics, or forced sidebars on small screens.
window.AscendContext = (() => {
  const main = document.querySelector('main');
  const frame = document.createElement('div'); frame.className = 'workspace-layout';
  const primary = document.createElement('div'); primary.className = 'workspace-primary';
  const rail = document.createElement('aside'); rail.className = 'context-rail'; rail.setAttribute('aria-label', 'Page context');
  primary.append(...main.querySelectorAll('.screen')); frame.append(primary, rail); main.append(frame);
  let observer;
  const section = title => { const node = el('section', undefined, 'context-section'); node.append(el('h2', title)); rail.append(node); return node; };
  function link(host, text, action) { host.append(button(text, action, 'text-button context-link')); }
  function position(host, stats) {
    const nodes = (stats.levels || []).filter(lv => lv.lane === 'main').flatMap(lv => lv.nodes);
    if (!nodes.length) return;
    const p = progressOf(nodes), display = el('div', undefined, 'context-progress');
    const art = svgElement('svg', {viewBox: '0 0 64 64', width: 64, height: 64, 'aria-hidden': 'true'});
    art.append(svgElement('circle', {cx:32, cy:32, r:26, fill:'none', stroke:'var(--divider)', 'stroke-width':5}));
    art.append(svgElement('circle', {cx:32, cy:32, r:26, fill:'none', stroke:'var(--success)', 'stroke-width':5, pathLength:100, 'stroke-dasharray': `${p.percent} 100`, transform:'rotate(-90 32 32)', class:'context-progress-ring'}));
    const value = el('div'); value.append(el('strong', `${p.done} / ${p.total}`), el('span', 'challenges complete', 'small muted'));
    display.append(art, value); host.append(display);
  }
  function toc(screen, title = 'On this page') {
    const scope = screen.id === 'docs' ? screen.querySelector('#docs-article') : screen;
    const headings = [...scope.querySelectorAll('h2')].filter(h => !h.closest('[hidden], .pg-catalog-card, .lab-notebook, .pg-tour, details:not([open])')).slice(0, 8);
    if (!headings.length) return;
    const host = section(title), nav = el('nav'); nav.setAttribute('aria-label', title); host.append(nav);
    const links = [];
    let clickedHeading = null, followClickUntil = 0;
    for (const [i, heading] of headings.entries()) {
      if (!heading.id) heading.id = `context-${screen.id}-${i}`;
      const anchor = el('a', heading.textContent); anchor.href = `#${heading.id}`;
      anchor.addEventListener('click', event => {
        event.preventDefault();
        clickedHeading = heading; followClickUntil = performance.now() + 700;
        for (const item of links) {
          if (item.heading === heading) item.anchor.setAttribute('aria-current', 'location'); else item.anchor.removeAttribute('aria-current');
        }
        heading.tabIndex = -1; heading.focus({preventScroll:true});
        heading.scrollIntoView({block:'start', behavior:document.documentElement.dataset.motion === 'off' ? 'instant' : 'smooth'});
      }); nav.append(anchor); links.push({anchor, heading});
    }
    observer = new IntersectionObserver(entries => {
      const entry = entries.find(item => item.isIntersecting
        && (performance.now() >= followClickUntil || item.target === clickedHeading));
      if (!entry) return;
      for (const item of links) {
        if (item.heading === entry.target) item.anchor.setAttribute('aria-current', 'location'); else item.anchor.removeAttribute('aria-current');
      }
    }, {rootMargin: '-100px 0px -45% 0px'});
    headings.forEach(heading => observer.observe(heading));
  }
  function render() {
    observer?.disconnect(); rail.replaceChildren(); frame.dataset.context = state.tab;
    const screen = document.getElementById(state.tab);
    if (!screen || state.tab === 'challenge') return;
    if (state.tab === 'today' || state.tab === 'stats') {
      const host = section(state.tab === 'today' ? 'Your momentum' : 'Keep building');
      const streak = el('p', undefined, 'context-streak'); streak.append(icon('flame'), el('strong', `${state.overview?.current_streak || 0}`), document.createTextNode('day streak')); host.append(streak);
      position(host, state);
      if (state.tab === 'today') link(host, 'See your progress →', () => switchTab('stats'));
      else link(host, 'Choose your next step →', () => switchTab('today'));
      const next = section('Where to next?');
      if (state.overview?.mission) { next.append(el('p', state.overview.mission.title, 'context-caption')); link(next, 'Open learning path →', () => switchTab('path')); }
      link(next, 'Explore Playground →', () => playgroundOpen('quick'));
      if (state.tab === 'stats') toc(screen);
    } else if (state.tab === 'path') {
      const host = section('Your route'); position(host, state);
      const levels = el('nav'); levels.setAttribute('aria-label', 'Jump to a level'); host.append(levels);
      for (const [i, level] of state.levels.filter(lv => lv.lane === 'main').entries()) {
        link(levels, `${i + 1}. ${level.title}`, () => jumpToLevel(level.id));
      }
    } else if (state.tab === 'docs') {
      toc(screen);
      const host = section('Keep this guide');
      const anchor = el('a', 'Copy guide link', 'context-action'); anchor.href = location.href;
      anchor.addEventListener('click', async event => { event.preventDefault(); try { await navigator.clipboard.writeText(location.href); notify('Guide link copied.', 'success'); } catch { notify('Copy the address from your browser to keep this guide.'); } }); host.append(anchor);
    } else if (state.tab === 'profile') {
      toc(screen, 'Your settings'); const host = section('Your learning day');
      host.append(icon('sun'), el('p', state.account?.settings?.timezone || 'Your account timezone', 'context-caption'), el('p', 'A new learning day begins at 4 AM.', 'small muted'));
      const anchor = el('a', 'Profile guide →', 'context-action'); anchor.href = '#docs/profile'; host.append(anchor);
    } else if (state.tab === 'more') {
      toc(screen, 'Track library'); const host = section('Your active track');
      host.append(el('p', state.overview?.mission?.title || 'Choose a domain to find your first track.', 'context-caption'));
      if (state.overview?.mission) { position(host, state); link(host, 'Continue learning →', () => switchTab('today')); }
      const anchor = el('a', 'Guide to tracks →', 'context-action'); anchor.href = '#docs/packs'; host.append(anchor);
    } else if (state.tab === 'playground') {
      const host = section('Find your next activity');
      for (const [route, label] of [['quick', 'Learn with guidance'], ['challenges', 'Test your understanding'], ['free', 'Experiment freely'], ['history', 'Return to saved work']]) {
        link(host, label, () => playgroundOpen(route));
      }
      const saved = section('Keep your place');
      saved.append(el('p', 'Your answers, notes and experiments stay in Saved work & history.', 'small muted'));
      link(saved, 'Open saved work →', () => playgroundOpen('history'));
      toc(screen, 'Browse this page');
    } else if (state.tab === 'lab') {
      toc(screen, 'In this lab'); const host = section('Keep your place');
      link(host, 'Browse Linux labs →', () => playgroundOpen('labs'));
      const anchor = el('a', 'Setup & cleanup guide →', 'context-action'); anchor.href = '#docs/linux-labs'; host.append(anchor);
    } else if (state.tab === 'attempts') {
      const host = section('Saved work'); link(host, 'All activity groups →', () => playgroundOpen('history'));
      host.append(el('p', 'Each attempt keeps its own work, result and timer.', 'small muted'));
    } else if (state.tab === 'activity') {
      toc(screen, 'In this activity'); const host = section('Your workspace');
      host.append(el('p', 'Work saves as you go. Return through Saved work & history.', 'small muted'));
      link(host, 'Saved work & history →', async () => { await savePlaygroundDraft(true); await playgroundOpen('history'); });
    }
  }
  return {render};
})();
