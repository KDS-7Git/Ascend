"use strict";
// Presentation only: all learning state and actions come from the existing app.
// No requests, storage, reward arithmetic, or authentication belong in this module.
window.AscendWorkspace = (() => {
  const root = document.documentElement;
  const colorScheme = matchMedia('(prefers-color-scheme: dark)');
  const make = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  function syncTheme() {
    root.dataset.workspaceTheme = root.dataset.theme === 'dark' || (!root.dataset.theme && colorScheme.matches) ? 'dark' : 'light';
  }
  new MutationObserver(syncTheme).observe(root, {attributes:true, attributeFilter:['data-theme']});
  colorScheme.addEventListener('change', syncTheme);
  syncTheme();
  const backdrop = make('div', undefined, 'ws-backdrop');
  backdrop.setAttribute('aria-hidden', 'true');
  backdrop.inert = true;
  backdrop.innerHTML = `  <svg class="ws-landscape" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><pattern id="ws-paper-crosses" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M38 40h4m-2-2v4" class="ws-map-stroke"/></pattern></defs>
    <rect width="1600" height="1000" fill="url(#ws-paper-crosses)"/>
    <g class="ws-terrain-contours"><path d="M810-50c100 130 120 190 280 165s160 140 420 100 260 180 160 320"/><path d="M880-50c60 110 110 160 240 145s155 125 390 90 240 170 150 320"/><path d="M950-50c35 95 80 115 200 125s120 110 340 90 230 160 145 300"/><path d="M1020-50c25 70 75 100 170 110s105 80 285 80 200 150 135 270"/>
    <path d="M-150 640c200-90 140 160 330 100s330 100 425 240"/><path d="M-150 685c190-90 145 150 330 100s300 80 370 220"/><path d="M-150 730c185-80 145 140 330 90s265 60 320 190"/></g>
    <g class="ws-terrain-markers"><circle cx="1430" cy="94" r="68"/><path d="m1350 804 80-135 90 152H1320l30-17Z"/><path d="m1343 891 34-60 40 70h-83l9-10Z"/></g>
  </svg>
  <div class="ws-night-atmosphere" aria-hidden="true">
    <svg class="ws-night-ribbons" viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id="ws-night-flow" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#40d7bd" stop-opacity=".02"/><stop offset=".48" stop-color="#6986ff" stop-opacity=".25"/><stop offset=".8" stop-color="#d68fff" stop-opacity=".35"/><stop offset="1" stop-color="#fff4d4" stop-opacity=".04"/></linearGradient>
        <linearGradient id="ws-night-edge" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#c3b0ff" stop-opacity=".02"/><stop offset=".55" stop-color="#d5bbff" stop-opacity=".42"/><stop offset="1" stop-color="#6ae6d5" stop-opacity=".07"/></linearGradient>
      </defs>
      <path d="M-170 1070C100 1090 680 510 1090 350S1570 460 1770-90" fill="none" stroke="url(#ws-night-flow)" stroke-width="190"/>
      <path d="M-170 975C100 995 680 415 1090 255S1570 365 1770-185" fill="none" stroke="url(#ws-night-edge)" stroke-width="2"/>
      <path d="M530-110C850 155 1260-20 1460 195S1310 670 1750 780" fill="none" stroke="url(#ws-night-flow)" stroke-width="78"/>
      <path d="M530-149C850 116 1260-59 1460 156S1310 631 1750 741" fill="none" stroke="url(#ws-night-edge)" stroke-width="1.5"/>
    </svg>
  </div>
`;
  document.body.prepend(backdrop);
  function companionMarkup() {
  return `<svg viewBox="0 0 260 240" fill="none" aria-hidden="true">
    <ellipse cx="133" cy="215" rx="99" ry="15" fill="#09261d" opacity=".16"/>
    <path d="m24 199 111-41 106 37-109 37-108-33Z" fill="#49684c"/>
    <path d="m24 193 111-41 106 37-109 37-108-33Z" fill="#a5bc8b"/>
    <path d="m40 193 95-34 90 31-94 31-91-28Z" stroke="#d6dfb9" opacity=".45"/>
    <path d="M85 183h25q13 0 13-13v-8" stroke="#e0d1a9" stroke-width="4" stroke-linecap="round"/>
    <path d="m173 172 21 7v15l-21-7v-15Z" fill="#47695b"/><path d="m173 172 18-7 21 7-18 7-21-7Z" fill="#b0c6b5"/><path d="m194 179 18-7v15l-18 7v-15Z" fill="#748f7b"/>
    <path d="m173 154 21 7v15l-21-7v-15Z" fill="#47695b"/><path d="m173 154 18-7 21 7-18 7-21-7Z" fill="#ccd7bf"/><path d="m194 161 18-7v15l-18 7v-15Z" fill="#91a68c"/>
    <circle class="ws-signal" cx="181" cy="161" r="2" fill="#e6eb9c"/><circle cx="181" cy="179" r="2" fill="#e6eb9c"/>
    <path d="m42 167 22 8v24l-22-8v-24Z" fill="#384d49"/><path d="m42 167 19-7 22 8-19 7-22-8Z" fill="#dfd5e7"/><path d="m64 175 19-7v24l-19 7v-24Z" fill="#a7a0bc"/>
    <path d="m48 178 10 4m-10 3 10 4" stroke="#a3b797" stroke-width="2"/>
    <path d="M115 169v19m33-21v18" stroke="#283e30" stroke-width="8" stroke-linecap="round"/>
    <path d="m107 190 14 1m20-3 14 1" stroke="#26382c" stroke-width="9" stroke-linecap="round"/>
    <path d="m92 115-9 16 9 12" stroke="#efbd61" stroke-width="9" stroke-linecap="round"/>
    <rect x="94" y="67" width="72" height="106" rx="23" fill="#ddab50"/>
    <rect x="88" y="65" width="72" height="106" rx="23" fill="#f2d27c"/>
    <path d="M109 70V52" stroke="#b4c792" stroke-width="5" stroke-linecap="round"/>
    <circle cx="109" cy="48" r="7" fill="#ddecba"/>
    <rect x="98" y="91" width="52" height="33" rx="12" fill="#334f3d"/>
    <g class="ws-eye" fill="#f6f5d7"><ellipse cx="113" cy="106" rx="4" ry="6"/><ellipse cx="137" cy="106" rx="4" ry="6"/></g>
    <path d="M120 115h8" stroke="#d4e1b3" stroke-width="2" stroke-linecap="round"/>
    <rect x="111" y="135" width="27" height="16" rx="5" fill="#e6b95c"/>
    <path d="m119 142 4-4 5 4" stroke="#916e30" stroke-width="1.7" stroke-linecap="round"/>
    <g class="ws-hand"><path d="M160 123q19 9 24-11" stroke="#edc467" stroke-width="9" stroke-linecap="round"/><path d="M184 111V66" stroke="#334b34" stroke-width="3" stroke-linecap="round"/><path d="m185 66 33 4-7 10 5 8-31-3V66Z" fill="#c4b4e0"/><path d="m193 76 4 4 8-7" stroke="#4f5538" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>
    <path d="m215 209 1-16m-1 9-6-7m7 3 5-9" stroke="#506a42" stroke-width="3" stroke-linecap="round"/>
  </svg>`;
  }
  function companion() {
    const frame = make('div', undefined, 'challenge-art ws-companion');
    frame.setAttribute('aria-hidden', 'true');
    frame.innerHTML = companionMarkup();
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
  return {companion, renderToday, decoratePath};
})();
