"use strict";
const $ = (selector, root = document) => root.querySelector(selector);
const state = {token: sessionStorage.getItem("ascend-token"), minutes: null, overview: null, levels: [], tab: "today", account: null, guides: null, guideTopic: null, installedPacks: [], showAllPacks: false};
const TABS = ["today", "path", "playground", "activity", "lab", "attempts", "stats", "more", "docs", "profile", "challenge"];
const TAB_NAMES = {today: "Today", path: "Learning path", playground: "Playground", activity: "Playground activity", lab: "Linux lab", attempts: "Activity attempts", stats: "Progress", more: "Tracks", docs: "Documentation", profile: "Profile", challenge: "Challenge"};
let noticeTimer;
let challengeIntroPlayed = false;
let challengeIntroObserver;
let navigationVersion = 0;
const SERVER_UPDATE_REQUIRED = 'The running Ascend server has not loaded this update. Restart the server, then reload this page.';
function el(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
async function runAction(node, action, after) {
  if (node.getAttribute('aria-busy') === 'true') return;
  const disabled = node.disabled;
  node.disabled = true;
  node.setAttribute('aria-busy', 'true');
  try { await action(); } catch (error) { notify(error.message, 'error'); }
  finally { node.removeAttribute('aria-busy'); if (node.isConnected) node.disabled = disabled; if (after) after(); }
}
function button(text, action, className = "secondary") {
  const node = el("button", text, className);
  node.type = "button";
  node.addEventListener("click", () => runAction(node, action));
  return node;
}
function dismissNotice() {
  const node = $('#notice');
  clearTimeout(noticeTimer);
  node.hidden = true;
}
function notify(message, kind = 'info', options = {}) {
  const node = $('#notice');
  // A timer reminder must not replace an unresolved action error.
  if (kind === 'reminder' && !node.hidden && node.dataset.kind === 'error') return;
  delete node.dataset.bootNotice;
  const dialog = [...document.querySelectorAll('dialog[open]')].at(-1);
  (dialog?.querySelector('.dialog-feedback') || document.body).append(node);
  node.dataset.kind = kind;
  node.setAttribute('role', kind === 'error' ? 'alert' : 'status');
  node.setAttribute('aria-live', kind === 'error' ? 'assertive' : 'polite');
  $('.notice-message', node).textContent = message || 'The action could not be completed.';
  $('.notice-symbol', node).replaceChildren(icon(kind === 'success' ? 'check' : kind === 'error' ? 'warning' : 'info'));
  node.hidden = false;
  window.AscendFeedback?.notice(node, {kind, ...options});
  clearTimeout(noticeTimer);
  // Dialog feedback and errors stay until dismissed or replaced; no reading race.
  if (!dialog && kind !== 'error') noticeTimer = setTimeout(dismissNotice, 8000);
}
async function api(path, body, method = "POST", interactive = true) {
  const headers = {}; if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const options = {headers, cache: "no-store"};
  if (body !== undefined) { options.method = method; if (body instanceof FormData) options.body = body; else { headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); } }
  let response;
  try { response = await fetch(`/api/${path}`, {...options, signal: AbortSignal.timeout(15000)}); } catch { throw new Error("The server is not responding. Check your connection and try again."); }
  if (response.status === 401) { if (interactive && !$("#login-dialog").open) $("#login-dialog").showModal(); throw new Error("Sign in to continue."); }
  const data = await response.json();
  const route = path.split('?')[0];
  if (response.status === 404 && /^(playground|lab-catalog|lab-attempts|hosted-labs)(\/|$)/.test(route) && data.detail === 'Not Found') throw new Error(SERVER_UPDATE_REQUIRED);
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Please check the form fields.");
  if (route === 'stats' && (!data.xp || !data.playground)) throw new Error(SERVER_UPDATE_REQUIRED);
  return data;
}
const command = argv => api("command", {argv});
function currentRoute() {
  const [raw, topic] = location.hash.slice(1).split('/');
  return {tab: TABS.includes(raw) ? raw : 'today', topic: topic || null};
}
async function switchTab(tab, options = {}) {
  if (tab === 'playground' && options.topic && !['quick', 'challenges', 'free', 'labs', 'history'].includes(options.topic)) tab = 'activity';
  if (!TABS.includes(tab)) return;
  const version = ++navigationVersion;
  if (activeNotebook) {
    try { await flushChallengeNotebook(); } catch { notify('Your unsaved notes are kept in this browser. Reconnect to save them to your account.', 'error'); }
    if (tab !== 'challenge') activeNotebook = null;
  }
  if (state.tab === 'activity') await savePlaygroundDraft(tab !== 'activity' || (options.topic && options.topic !== state.activityRef));
  const previous = $('.screen:not([hidden])');
  if ($('#docs-menu').open) $('#docs-menu').close();
  if (tab === 'challenge' && $('#sheet').open) $('#sheet').close();
  const changed = state.tab !== tab;
  state.tab = tab;
  if (changed && document.documentElement.dataset.boot !== 'loading') await window.AscendMotion?.leave?.(previous);
  if (version !== navigationVersion) return;
  document.querySelectorAll('.screen').forEach(screen => screen.hidden = screen.id !== tab);
  document.querySelectorAll('.primary-nav [data-tab]').forEach(node => {
    const active = node.dataset.tab === (['activity', 'lab', 'attempts'].includes(tab) ? 'playground' : tab);
    node.classList.toggle('active', active);
    if (active) node.setAttribute('aria-current', 'page');
    else node.removeAttribute('aria-current');
  });
  if (tab === 'profile') $('#profile-link').setAttribute('aria-current', 'page');
  else $('#profile-link').removeAttribute('aria-current');
  $('#page-context').textContent = TAB_NAMES[tab];
  document.title = `${TAB_NAMES[tab]} · Ascend`;
  if (tab === 'docs') state.guideTopic = options.topic || state.guideTopic || 'getting-started';
  if (tab === 'challenge' && options.topic) state.challengeRef = decodeURIComponent(options.topic);
  if (tab === 'playground') state.playgroundRoute = options.topic || state.playgroundRoute || 'quick';
  if (tab === 'activity') state.activityRef = options.topic || state.activityRef;
  if (tab === 'lab') state.labRef = decodeURIComponent(options.topic || state.labRef || 'security-datasets');
  if (tab === 'attempts') state.attemptGroupRef = decodeURIComponent(options.topic || state.attemptGroupRef || '');
  const hash = tab === 'attempts' ? `attempts/${encodeURIComponent(state.attemptGroupRef)}` : tab === 'lab' ? `lab/${encodeURIComponent(state.labRef)}` : tab === 'activity' ? `activity/${state.activityRef}` : tab === 'playground' ? `playground/${state.playgroundRoute}` : tab === 'docs' ? `docs/${state.guideTopic}` : tab === 'challenge' && state.challengeRef ? `challenge/${encodeURIComponent(state.challengeRef)}` : tab;
  if (location.hash !== `#${hash}`) location.hash = hash;
  if (changed) window.scrollTo({top: 0, behavior: 'instant'});
  const screen = document.getElementById(tab);
  screen.setAttribute('aria-busy', 'true');
  $('#route-progress').hidden = false;
  const loadingTimer = setTimeout(() => { screen.dataset.loading = 'true'; }, 160);
  try {
  if (tab === 'docs') {
    await renderDocs();
    if (state.tab === tab && version === navigationVersion) window.AscendMotion?.enter?.($('#docs'), `docs/${state.guideTopic}`);
    renderSessionClock();
    if (!state.account) refreshDocsChrome().catch(() => {});
    return;
  }
  if (!state.overview) await refresh();
  if (tab === 'today') playChallengeIntro();
  if (tab === 'path') await renderPath();
  if (tab === 'stats') await renderStats();
  if (tab === 'more') await renderMore();
  if (tab === 'profile') await renderProfile();
  if (tab === 'challenge') await renderChallenge();
  if (tab === 'playground') await renderPlayground();
  if (tab === 'activity') await renderActivity();
  if (tab === 'lab') await renderLabDetail();
  if (tab === 'attempts') await renderAttemptGroup();
  renderSessionClock();
  if (state.tab === tab && version === navigationVersion) window.AscendMotion?.enter?.(document.getElementById(tab), tab);
  } catch (error) {
    if (version === navigationVersion && state.tab === tab && ['playground', 'activity', 'lab', 'attempts', 'stats'].includes(tab)) {
      const panel = el('section', undefined, 'card empty'); panel.setAttribute('role', 'alert');
      panel.append(el('h2', 'This page could not load'), el('p', error.message), button('Try again', () => switchTab(tab, options), ''));
      $(`#${tab}-content`).replaceChildren(panel);
      return;
    }
    throw error;
  } finally {
    clearTimeout(loadingTimer);
    if (version === navigationVersion) window.AscendContext?.render();
    delete screen.dataset.loading;
    screen.removeAttribute('aria-busy');
    if (version === navigationVersion) $('#route-progress').hidden = true;
  }
}
const ICONS = {
  menu: ['M4 6h16M4 12h16M4 18h16'],
  layers: ['m12 3 10 5-10 5L2 8l10-5Z', 'm2 12 10 5 10-5M2 16l10 5 10-5'],
  plus: ['M12 5v14M5 12h14'],
  info: ['M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18', 'M12 11v6m0-10v1'],
  warning: ['m12 3 10 18H2L12 3Z', 'M12 9v5m0 3v1'],
  sun: ['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8', 'M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5'],
  route: ['M5 4a2 2 0 1 0 0 4 2 2 0 0 0 0-4M19 16a2 2 0 1 0 0 4 2 2 0 0 0 0-4', 'M7 6h9a4 4 0 0 1 0 8H8a2 2 0 0 0 0 4h9'],
  chart: ['M4 4v16h16M8 15v-3m5 3V8m5 7V5'],
  settings: ['M4 7h16M4 17h16M9 4v6m6 4v6'],
  mountain: ['m2 20 8-15 5 9 3-5 4 11H2', 'm7 11 3 2 3-2'],
  flame: ['M12 3c1 6 6 6 6 12a6 6 0 0 1-12 0c0-3 2-5 3-6 0 3 2 3 3 0V3Z'],
  check: ['m5 12 4 4L19 6'],
  lock: ['M7 10V7a5 5 0 0 1 10 0v3M5 10h14v11H5V10Zm7 4v3'],
  flag: ['M5 22V3m0 0c5-4 9 4 15 0v10c-6 4-10-4-15 0'],
  arrow: ['M4 12h16m-6-6 6 6-6 6'],
  bolt: ['m13 2-9 12h7l-1 8 10-13h-7l1-7'],
  play: ['m8 4 12 8-12 8V4Z'],
  book: ['M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2V4Zm9 2v15']
};
function svgElement(tag, attrs = {}) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  return node;
}
function icon(name, className = '') {
  const svg = svgElement('svg', {viewBox: '0 0 24 24', width: 22, height: 22, fill: 'none', stroke: 'currentColor', 'stroke-width': 1.7, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', class: `icon ${className}`});
  for (const d of ICONS[name] || ICONS.flag) svg.append(svgElement('path', {d}));
  return svg;
}
function progressOf(nodes) {
  const done = nodes.filter(n => n.status === 'done').length;
  const skipped = nodes.filter(n => n.status === 'skipped').length;
  return {done, skipped, total: nodes.length, percent: nodes.length ? Math.round(done / nodes.length * 100) : 0, resolved: done + skipped};
}
function progressLabel(p) { return `${p.done}/${p.total} complete${p.skipped ? ` · ${p.skipped} skipped` : ''}`; }
function progressBar(nodes, label) {
  const p = progressOf(nodes), bar = el('progress', undefined, 'progress');
  bar.max = p.total || 1; bar.value = p.done; bar.setAttribute('aria-label', label); return bar;
}
function currentLevel() {
  const main = state.levels.filter(lv => lv.lane === 'main');
  return main.find(lv => lv.id === state.overview?.next?.level) || main.find(lv => lv.open && lv.nodes.some(n => n.status === 'todo')) || main.at(-1);
}
function levelFor(node) { return state.levels.find(lv => lv.id === node.level); }
function fullNode(node) { return levelFor(node)?.nodes.find(n => n.id === node.id) || node; }
let refreshVersion = 0;
async function refresh() {
  const version = ++refreshVersion;
  const [overview, levels, account, practice] = await Promise.all([api('me' + (state.minutes ? `?minutes=${state.minutes}` : '')), api('levels'), api('account'), api(`playground/recommendations?kind=&minutes=${state.minutes || 1440}`)]);
  if (version !== refreshVersion) return;
  overview.practice = practice;
  if (state.overview?.mission?.id !== overview.mission?.id) $('#session-result').hidden = true;
  state.overview = overview; state.levels = levels; state.account = account;
  updateAccountChrome();
  updateStreak(overview.current_streak);
  renderMissionProgress();
  const cards = $('#today-cards'); cards.replaceChildren();
  const limited = state.minutes && overview.next?.estimate > Number(state.minutes);
  const fitting = limited ? timeFitChoice(overview, Number(state.minutes)) : null;
  if (limited) cards.append(timeFitCard(overview, Number(state.minutes), fitting));
  else if (overview.next) cards.append(nodeCard(overview.next, false));
  else {
    const main = levels.filter(lv => lv.lane === 'main').flatMap(lv => lv.nodes), p = progressOf(main);
    const finished = main.length && p.resolved === p.total;
    const empty = el('div', undefined, 'card empty'); empty.append(icon(finished ? 'flag' : 'mountain'));
    empty.append(el('h2', !overview.mission ? 'Find your first summit.' : finished ? (p.skipped ? 'Your main path is explored.' : 'Your main path is complete!') : 'Your next step is waiting.'), el('p', !overview.mission ? 'Choose a track, or start a short activity in Playground.' : finished ? 'Keep practicing in Playground or choose your next mission.' : 'Explore your path to check its prerequisites. Playground practice is available whenever you want a detour.'));
    empty.append(button(overview.mission ? 'Explore your path' : 'Choose a track', () => switchTab(overview.mission ? 'path' : 'more'), ''));
    cards.append(empty);
  }
  const aside = el('aside', undefined, 'today-aside'); aside.setAttribute('aria-label', 'More ways to keep learning');
  if (fitting?.kind !== 'practice') aside.append(playgroundRecommendation(overview.practice, state.minutes ? Number(state.minutes) : null, {kind: ''}));
  if (overview.checkpoint && fitting?.kind !== 'checkpoint') {
    const suggestion = overview.checkpoint, part = suggestion.checkpoint;
    const card = el('section', undefined, 'card pg-recommendation');
    card.append(el('p', 'A SMALL PART OF YOUR TRACK', 'eyebrow'), el('h2', part.title), el('p', `${part.minutes} min checkpoint · ${suggestion.title} remains about ${suggestion.full_minutes} min in total.`, 'small muted'), button('Open checkpoint', () => openCheckpoints(suggestion.reference), ''));
    aside.append(card);
  }
  if (overview.quick_win && fitting?.kind !== 'side') aside.append(nodeCard(overview.quick_win, true));
  const lv = currentLevel(), milestone = lv?.nodes.find(n => n.milestone && n.status === 'todo');
  if (milestone && milestone.id !== overview.next?.id) {
    const target = el('section', undefined, 'card summit-card');
    const label = el('p', undefined, 'eyebrow'); label.append(icon('flag'), document.createTextNode('YOUR NEXT MILESTONE'));
    target.append(label, el('h2', milestone.title.replace(/\s*\(milestone\)$/i, '')));
    target.append(progressBar(lv.nodes, `${lv.title} progress`), el('p', progressLabel(progressOf(lv.nodes)), 'small muted'), button('Preview milestone', () => showNode(milestone, lv), 'text-button'));
    aside.append(target);
  }
  if (aside.childElementCount) cards.append(aside);
  playChallengeIntro();
  await refreshSessions();
  window.AscendContext?.render();
}
async function playChallengeIntro() {
  challengeIntroObserver?.disconnect();
  const card = $('.next-card');
  if (challengeIntroPlayed || state.tab !== 'today' || !card || document.documentElement.dataset.boot === 'loading') return;
  await document.fonts.ready;
  if (challengeIntroPlayed || state.tab !== 'today' || card !== $('.next-card')) return;
  challengeIntroObserver?.disconnect();
  if (document.documentElement.dataset.motion === 'off' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    challengeIntroPlayed = true;
    return;
  }
  const start = () => {
    challengeIntroObserver?.disconnect();
    challengeIntroPlayed = true;
    if (document.documentElement.dataset.motion === 'off' || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const finish = event => {
      if (event.target !== card || event.animationName !== 'challenge-border-sweep') return;
      card.removeEventListener('animationend', finish);
      card.removeEventListener('animationcancel', finish);
      card.classList.remove('challenge-intro');
    };
    card.addEventListener('animationend', finish);
    card.addEventListener('animationcancel', finish);
    card.classList.add('challenge-intro');
  };
  // On a phone the card may begin below the fold. Do not spend its one sweep unseen.
  if (!('IntersectionObserver' in window)) { start(); return; }
  challengeIntroObserver = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting && entry.intersectionRatio >= .2) && card.isConnected && state.tab === 'today') start();
  }, {threshold: .2, rootMargin: '-72px 0px -80px 0px'});
  challengeIntroObserver.observe(card);
}
function renderMissionProgress() {
  const root = $('#mission-progress'); root.replaceChildren();
  if (!state.overview.mission) return;
  const levels = state.levels.filter(lv => lv.lane === 'main'), current = currentLevel();
  const nodes = levels.flatMap(lv => lv.nodes), p = progressOf(nodes);
  const banner = el('section', undefined, 'mission-banner');
  const emblem = el('div', undefined, 'mission-emblem'); emblem.append(icon('route'));
  const info = el('div', undefined, 'mission-info'); info.append(el('p', 'YOUR ACTIVE TRACK', 'eyebrow'), el('h2', state.overview.mission.title), el('p', current ? `Level ${levels.indexOf(current) + 1} of ${levels.length}` : 'Ready when you are', 'muted small'));
  const meta = el('div', undefined, 'mission-meta'); meta.append(el('strong', `${p.percent}%`), el('span', progressLabel(p), 'small muted'));
  const milestones = el('div', undefined, 'level-dots');
  for (const [index, lv] of levels.entries()) {
    const done = lv.nodes.every(n => n.status === 'done');
    const dot = button(String(index + 1), async () => { await switchTab('path'); jumpToLevel(lv.id); }, `level-dot${done ? ' done' : ''}${lv.id === current?.id ? ' current' : ''}`);
    dot.setAttribute('aria-label', `Level ${index + 1}: ${lv.title}${done ? ', complete' : ''}`);
    if (done) dot.replaceChildren(icon('check')); milestones.append(dot);
  }
  info.append(milestones); banner.append(emblem, info, meta); root.append(banner);
}
function timeFitChoice(overview, minutes) {
  if (overview.checkpoint?.checkpoint.minutes <= minutes) return {kind: 'checkpoint', item: overview.checkpoint.checkpoint};
  if (overview.quick_win?.estimate <= minutes) return {kind: 'side', item: overview.quick_win};
  const activity = overview.practice?.activities?.find(item => (item.selection_minutes || item.minutes) <= minutes);
  return activity ? {kind: 'practice', item: activity} : null;
}
function timeFitCard(overview, minutes, choice, excluded = []) {
  const card = el('article', undefined, 'card node-card next-card time-fit-card');
  const label = el('p', undefined, 'eyebrow'); label.append(icon('bolt'), document.createTextNode(`FOR YOUR ${minutes} MINUTES`)); card.append(label);
  const item = choice?.item;
  card.append(el('h2', item ? compactTitle(item.title) : 'No ready task fits this time.'));
  if (item) {
    const duration = item.selection_minutes || item.minutes || item.estimate;
    card.dataset.suggestedMinutes = duration;
    const meta = el('div', undefined, 'challenge-meta');
    meta.append(el('span', `~${duration} min`, 'pill'), el('span', choice.kind === 'checkpoint' ? 'Track checkpoint' : choice.kind === 'side' ? 'Optional track practice' : playgroundLabel(item), 'small'));
    card.append(meta);
  }
  card.append(el('p', `Your next full track challenge needs about ${overview.next.estimate} minutes. ${item ? 'This activity fits your selected time.' : 'Choose more time, or come back when you’re ready.'}`, 'time-fit-note'));
  card.append(challengeIllustration());
  const actions = el('div', undefined, 'card-actions');
  if (choice) {
    const open = button(choice.kind === 'checkpoint' ? 'Open checkpoint' : choice.kind === 'side' ? 'Open challenge' : item.role === 'example' ? 'Start guided example' : 'Start practice', () => choice.kind === 'checkpoint' ? openCheckpoints(overview.checkpoint.reference) : choice.kind === 'side' ? showNode(fullNode(item), levelFor(item)) : startPlayground(item), '');
    open.append(icon('arrow')); actions.append(open);
    if (choice.kind === 'practice') actions.append(button('Choose another', async () => {
      const skip = [...excluded, item.id];
      const result = await api(`playground/recommendations?kind=&minutes=${minutes}&exclude=${encodeURIComponent(skip.join(','))}`);
      if (!result.activities.length) { notify('You’ve seen the available suggestions. Browse all activities for more choices.'); return; }
      card.replaceWith(timeFitCard({...overview, practice: result}, minutes, {kind: 'practice', item: result.activities[0]}, skip));
    }, 'text-button'));
  }
  actions.append(button('Choose more time', () => {
    const picker = $('.time-chips'); picker.scrollIntoView({block: 'center', behavior: 'instant'});
    picker.querySelector(`[data-minutes="${[30, 120].find(value => value >= overview.next.estimate) || ''}"]`)?.focus({preventScroll: true});
  }, choice ? 'text-button' : ''));
  const browse = el('a', 'Browse activities', 'subtle-link'); browse.href = '#playground/quick'; actions.append(browse);
  card.append(actions); return card;
}
function nodeCard(node, quick) {
  const card = el('article', undefined, `card node-card ${quick ? 'quick-card' : 'next-card'}${node.milestone ? ' milestone-hero' : ''}`);
  const label = el('p', undefined, 'eyebrow'); label.append(icon(quick ? 'bolt' : node.milestone ? 'flag' : 'play'), document.createTextNode(quick ? 'A LITTLE SIDE QUEST' : node.milestone ? 'MILESTONE CHALLENGE' : 'YOUR NEXT CHALLENGE'));
  card.append(label);
  const lv = levelFor(node);
  card.append(el('h2', compactTitle(node.title)));
  const meta = el('div', undefined, 'challenge-meta'); meta.append(el('span', `~${node.estimate} min`, 'pill'));
  if (!quick) meta.append(el('span', node.verify?.exercise === 'case' ? 'Knowledge check' : node.verify?.type === 'lab' ? 'Hands-on exercise' : 'Practice', 'small'));
  if (quick) meta.append(el('span', 'Optional', 'small'));
  card.append(meta);
  if (!quick) card.append(challengeIllustration());
  const actions = el('div', undefined, 'card-actions');
  const open = button(quick ? 'Try this challenge' : 'Open challenge', () => showNode(fullNode(node), lv), quick ? 'secondary' : ''); open.append(icon('arrow'));
  open.dataset.challenge = `${node.pack_id}:${node.id}`; open.dataset.defaultLabel = quick ? 'Try this challenge' : 'Open challenge';
  actions.append(open, button('Log progress', () => openLog(node), 'text-button')); card.append(actions);
  return card;
}
function compactTitle(title) { return title.replace(/^(Reason it through|Investigate|Practice):\s*/i, '').replace(/\s*\(milestone\)$/i, ''); }
function challengeIllustration() {
  const art = svgElement('svg', {viewBox: '0 0 220 180', width: 220, height: 180, class: 'challenge-art', 'aria-hidden': 'true'});
  const group = svgElement('g', {stroke: 'currentColor', 'stroke-width': 2, 'stroke-linejoin': 'round'});
  for (const [x, y, color] of [[18, 125, 'var(--mint)'], [80, 88, 'var(--soft)'], [142, 48, 'var(--action)']]) {
    group.append(svgElement('path', {d: `M${x} ${y}h44v38h-44z`, fill: color, class: 'ascent-step'}));
  }
  group.append(svgElement('path', {d: 'M163 47V15m0 0h29l-7 10 7 10h-29', fill: 'var(--peach)', class: 'ascent-flag'}));
  group.append(svgElement('rect', {x: 33, y: 111, width: 14, height: 14, rx: 2, fill: 'var(--accent)', class: 'ascent-climber'}));
  art.append(group); return art;
}
function openSheet(context = 'Challenge') {
  const dialog = $('#sheet');
  dismissNotice();
  $('#dialog-context').textContent = context;
  $('#sheet-content').replaceChildren();
  $('#sheet-content').scrollTop = 0;
  if (!dialog.open) dialog.showModal();
  // Focus the new heading after the caller fills the dialog. Closing returns
  // focus to the control that opened it, as prescribed by the native dialog.
  queueMicrotask(() => {
    const heading = $('#sheet-title');
    if (context === 'Log progress' && $('#learned')) $('#learned').focus({preventScroll: true});
    else if (heading) { heading.tabIndex = -1; heading.focus({preventScroll: true}); }
  });
  return $('#sheet-content');
}
function field(form, name, label, type = 'text', value = '') {
  const lbl = el('label', label); lbl.htmlFor = name;
  const input = el(type === 'textarea' ? 'textarea' : 'input'); input.id = name; input.name = name;
  if (type !== 'textarea') input.type = type; input.value = value;
  form.append(lbl, input); return input;
}
function showSessionResult(node, result, previousLevels) {
  const root = $('#session-result'); root.replaceChildren(); root.hidden = false; root.className = `session-result${result.completed ? ' completed' : ''}`;
  const badge = el('div', undefined, 'result-icon'); badge.append(icon(result.completed ? 'check' : 'book'));
  const copy = el('div'); copy.append(el('h2', result.completed ? (node.milestone ? 'Milestone reached!' : 'Challenge complete!') : 'Progress saved. Keep your place.'));
  const newlyOpen = state.levels.filter(lv => lv.lane === 'main' && lv.open && previousLevels.some(old => old.id === lv.id && !old.open));
  copy.append(el('p', result.completed ? `${node.title}${newlyOpen.length ? ` · Unlocked: ${newlyOpen.map(lv => lv.title).join(', ')}` : ' · One more skill put into practice.'}` : result.verification || 'Your work counts, even when the challenge takes another session.'));
  root.append(badge, copy, button('Dismiss', () => root.hidden = true, 'text-button'));
}
async function openLog(node) {
  await openChallengeNotes(node);
}
function instructionBlocks(text) {
  const fragment = document.createDocumentFragment();
  const fenced = /```([\w-]*)\n([\s\S]*?)```/g;
  let cursor = 0;
  const prose = value => { for (const paragraph of value.trim().split(/\n\s*\n/)) if (paragraph) fragment.append(el('p', paragraph)); };
  for (const match of text.matchAll(fenced)) {
    prose(text.slice(cursor, match.index));
    fragment.append(codeBlock(match[2].replace(/\n$/, ''), match[1] === 'json' ? 'JSON' : 'TERMINAL'));
    cursor = match.index + match[0].length;
  }
  prose(text.slice(cursor)); return fragment;
}
function codeBlock(text, label = 'COMMAND LINE') {
  const box = el('div', undefined, 'doc-code'), toolbar = el('div', undefined, 'code-toolbar');
  const copy = button('Copy', async () => {
    if (!navigator.clipboard) throw new Error('Copy is unavailable in this browser. Select the command text to copy it.');
    await navigator.clipboard.writeText(text); notify('Command copied.', 'success');
  }, 'text-button'); copy.setAttribute('aria-label', label === 'COMMAND LINE' ? 'Copy' : `Copy ${label.toLowerCase()} block`);
  toolbar.append(el('span', label), copy);
  const pre = el('pre'); pre.tabIndex = 0; pre.setAttribute('aria-label', `${label.toLowerCase()} block`); pre.append(el('code', text));
  box.append(toolbar, pre); return box;
}
function appendLearningResource(content, node) {
  if (!node.resource) return;
  const link = el('a', `${node.resource_label || 'Learning reference'} ↗`, 'resource-link');
  link.href = node.resource; link.target = '_blank'; link.rel = 'noopener noreferrer'; content.append(link);
  if (node.resource_note) content.append(el('p', node.resource_note, 'field-help'));
}
function showNode(node, level = levelFor(node), workspace = false, session = null) {
  const ref = `${node.pack_id}:${node.id}`;
  if (!workspace && [state.sessions?.active, ...(state.sessions?.paused || [])].some(item => item && `${item.pack_id}:${item.node_id}` === ref)) return switchTab('challenge', {topic: ref});
  const content = workspace ? $('#challenge-content') : openSheet(node.milestone ? 'Milestone' : 'Lesson'), status = node.status || 'todo';
  if (workspace) content.replaceChildren();
  content.append(el('p', `${node.milestone ? 'MILESTONE' : 'CHALLENGE'} · ~${node.estimate} MIN`, 'eyebrow'));
  const title = el(workspace ? 'h1' : 'h2', node.title); title.id = workspace ? 'challenge-title' : 'sheet-title'; content.append(title);
  const revealed = workspace && node.details_available;
  if (!revealed) {
    if (node.preview) content.append(el('p', node.preview, 'challenge-brief'));
    if (node.requirements) {
      const setup = el('section', undefined, 'challenge-setup');
      setup.append(el('h3', 'Required setup'), el('p', node.requirements)); content.append(setup);
    }
    appendLearningResource(content, node);
    content.append(el('p', node.has_attempt ? 'Open your attempt to review its instructions and saved progress.' : 'Start to open the task, files and instructions.', 'field-help'));
  } else {
    if (node.brief && !node.done_when.startsWith(node.brief)) content.append(el('p', node.brief, 'challenge-brief'));
    const outcome = el('section', undefined, 'outcome'); outcome.append(el('h3', 'Your finish line'), el('p', node.done_when)); content.append(outcome); content.append(el('p', verificationLabel(node), 'verification-label'));
    if (node.setup) { const setup = el('section', undefined, 'challenge-setup'); setup.append(el('h3', 'Workspace setup'), instructionBlocks(node.setup)); content.append(setup); }
    if (node.materials?.length) {
      const materials = el('ul', undefined, 'challenge-materials');
      for (const material of node.materials) {
        const item = el('li'), link = el('a', material.label, 'resource-link'); link.href = material.url;
        if (material.url.startsWith('/training/')) link.download = ''; else { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
        item.append(link); materials.append(item);
      }
      content.append(materials);
    }
    if (node.steps?.length) {
      const list = el('ol', undefined, 'challenge-steps');
      for (const step of node.steps) { const item = el('li'); item.append(instructionBlocks(step)); list.append(item); }
      content.append(el('h3', 'What to do'), list);
    }
    appendLearningResource(content, node);
    if (node.hints?.length) {
      const hints = el('section', undefined, 'challenge-hints'); hints.append(el('h3', 'A nudge if you need one'));
      node.hints.forEach((hint, i) => { const details = el('details'); details.append(el('summary', `Hint ${i + 1}`), el('p', hint)); hints.append(details); }); content.append(hints);
    }
  }
  const locked = !node.open && status === 'todo';
  if (locked) {
    const all = state.levels.flatMap(lv => lv.nodes), missing = (node.needs || []).map(id => all.find(n => n.id === id)).filter(n => n && n.status === 'todo');
    content.append(el('p', missing.length ? `First complete: ${missing.map(n => n.title).join(', ')}.` : 'This challenge opens after the previous level’s milestone.', 'lock-note'));
  }
  const actions = el('div', undefined, 'dialog-actions');
  if (!locked && node.checkpoints?.length) actions.append(button('Work on a small checkpoint', () => openCheckpoints(ref)));
  if (!locked) {
    const target = !revealed && !node.has_attempt ? field(content, 'task-target-minutes', 'Session target (minutes)', 'number', node.estimate) : null;
    if (target) { target.min = 1; target.max = 1440; }
    if (target) content.append(el('p', 'The clock runs continuously after Start. Complete the task or end the session when you finish.', 'field-help'));
    if (!revealed && node.has_attempt) actions.append(button('Review attempt', () => switchTab('challenge', {topic: ref}), ''));
    else if (target) actions.append(button(node.verify?.type === 'lab' ? 'Start verified exercise' : 'Start timed task', async () => {
      if (!target.reportValidity()) return;
      await command([node.verify?.type === 'lab' ? 'lab' : 'session', 'start', ref, '--minutes', String(Number(target.value))]);
      await refreshSessions(); await switchTab('challenge', {topic: ref});
      $('#challenge-title')?.focus({preventScroll: true});
      window.AscendMotion?.feedback?.($('#task-session'), 'start');
    }, ''));

  }
  if (status !== 'todo') content.append(el('p', status === 'done' ? '✓ Completed. Revisit this whenever you want to practice.' : 'Skipped. You can return to this challenge at any time.', 'muted'));
  content.append(actions);
  const manage = el('details', undefined, 'manage-challenge'); manage.append(el('summary', 'Challenge options'));
  if (status === 'todo') {
    manage.append(button('Skip challenge', async () => { await api(`nodes/${node.pack_id}:${node.id}/mark`, {status: 'skipped'}); $('#sheet').close(); await refresh(); if (state.tab === 'path') await renderPath(); notify('Challenge skipped. You can return to it from your path.'); }));
    if (level && !level.open) manage.append(button('Unlock level early', async () => { await command(['unlock', level.id]); $('#sheet').close(); await refresh(); if (state.tab === 'path') await renderPath(); }));
    if (revealed && !['lab', 'ctf'].includes(node.verify?.type)) {
      const parts = field(manage, 'split-parts', 'Split into smaller steps (one per line)', 'textarea');
      manage.append(button('Save smaller steps', async () => { await command(['split', `${node.pack_id}:${node.id}`, ...parts.value.split('\n').filter(Boolean)]); $('#sheet').close(); await refresh(); if (state.tab === 'path') await renderPath(); }));
    }
  } else manage.append(button('Reopen challenge', async () => { await api(`nodes/${node.pack_id}:${node.id}/mark`, {status:'todo'}); $('#sheet').close(); await refresh(); if (state.tab === 'path') await renderPath(); }));
  content.append(manage);
}
async function openCheckpoints(reference) {
  const data = await api(`nodes/${encodeURIComponent(reference)}/checkpoints`);
  const root = openSheet('Track checkpoints'); const title = el('h2', data.title); title.id = 'sheet-title';
  root.append(title, el('p', `Full task: about ${data.full_minutes} minutes. Choose a useful stopping point below. Saving a checkpoint records partial learning; complete the parent task separately.`, 'muted'));
  if (state.sessions?.active) root.append(el('p', 'Your existing scored session clock is still running. Saving a checkpoint does not pause or reset it.', 'small'));
  for (const part of data.checkpoints) {
    const section = el('section', undefined, 'pg-reference'); section.append(el('h3', `${part.saved ? '✓ ' : ''}${part.title} · ${part.minutes} min`), el('p', part.done_when));
    if (part.saved) section.append(el('p', 'Partial learning saved. The parent task keeps its own finish line.', 'small muted'));
    else {
      const form = el('form');
      const learned = playgroundField(form, 'What did you observe or learn?', '', 'textarea'); learned.required = true; learned.minLength = 20;
      const minutes = playgroundField(form, 'Minutes spent (optional)', '', 'number'); minutes.min = 1; minutes.max = 1440;
      form.append(el('p', `When you return: ${part.next_step}`, 'small muted'));
      const submit = el('button', 'Save checkpoint note'); form.append(submit);
      form.addEventListener('submit', event => { event.preventDefault(); runAction(submit, async () => {
        await api(`nodes/${encodeURIComponent(reference)}/checkpoints/${part.id}`, {learned:learned.value, minutes:minutes.value ? Number(minutes.value) : null});
        await refresh(); await openCheckpoints(reference); notify('Checkpoint saved as partial progress. Find it in this task and your learning log.', 'success');
      }); }); section.append(form);
    }
    root.append(section);
  }
}
function jumpToLevel(id) {
  const target = document.getElementById(`level-${id}`);
  if (target) { target.open = true; target.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start'}); target.querySelector('summary').focus({preventScroll:true}); }
}
async function renderPath() {
  state.levels = await api('levels'); const root = $('#path-content'); root.replaceChildren();
  if (!state.levels.length) { const empty = el('div', undefined, 'empty'); empty.append(el('h2', 'Every path starts with a first step.'), el('p', 'Choose a track in More to see your learning path.'), button('Choose a track', () => switchTab('more'), '')); root.append(empty); $('#jump-current').hidden = true; return; }
  $('#jump-current').hidden = false;
  const main = state.levels.filter(lv => lv.lane === 'main'), current = currentLevel();
  const intro = el('div', undefined, 'path-intro'); intro.append(el('h2', state.overview.mission?.title || 'Your learning path'), el('p', `${main.length} levels · ${progressLabel(progressOf(main.flatMap(lv => lv.nodes)))}`, 'muted'));
  const legend = el('div', undefined, 'path-legend'); for (const [label, cls] of [['Complete','done'],['Ready to try','open'],['Coming up','locked'],['Milestone','milestone']]) legend.append(el('span', label, `legend-item ${cls}`)); intro.append(legend); root.append(intro);
  for (const [i, level] of main.entries()) {
    const p = progressOf(level.nodes), isCurrent = level.id === current?.id;
    const section = el('details', undefined, `level-section${isCurrent ? ' current-level' : ''}${!level.open ? ' locked-level' : ''}`); section.id = `level-${level.id}`; section.open = isCurrent;
    const header = el('summary', undefined, 'level-header');
    const number = el('span', String(i + 1).padStart(2, '0'), 'level-number');
    const text = el('div', undefined, 'level-title'); text.append(el('p', isCurrent ? 'YOU ARE HERE' : p.done === p.total ? 'LEVEL COMPLETE' : level.open ? 'READY TO EXPLORE' : 'COMING UP', 'eyebrow'), el('h2', level.title));
    const meta = el('span', progressLabel(p), 'level-count'); header.append(number, text, meta); section.append(header, progressBar(level.nodes, `${level.title} progress`));
    const list = el('div', undefined, 'path-nodes');
    for (const [index, node] of level.nodes.entries()) {
      const status = node.status !== 'todo' ? node.status : node.open ? 'open' : 'locked';
      const isNext = node.id === state.overview.next?.id;
      const item = button('', () => showNode(node, level), `path-node ${status} bend-${index % 4}${node.milestone ? ' milestone' : ''}${isNext ? ' next-node' : ''}`);
      const shape = el('span', undefined, 'node-shape'); shape.append(icon(status === 'done' ? 'check' : status === 'skipped' ? 'arrow' : node.milestone ? 'flag' : status === 'locked' ? 'lock' : 'play'));
      const copy = el('span', undefined, 'node-copy'); copy.append(el('strong', node.title), el('span', `${isNext ? 'Up next · ' : ''}${node.milestone ? 'Milestone · ' : ''}~${node.estimate} min · ${status === 'open' ? 'Ready to try' : status}`, 'small muted'));
      item.setAttribute('aria-label', `${node.title}, ${status}${node.milestone ? ', milestone' : ''}`); item.append(shape, copy); list.append(item);
    }
    section.append(list); root.append(section);
  }
  for (const level of state.levels.filter(lv => lv.lane === 'side')) {
    const anytime = el('details', undefined, 'anytime'); anytime.append(el('summary', `${level.title} · Optional practice`));
    const strip = el('div', undefined, 'anytime-strip');
    for (const node of level.nodes) { const status = node.status === 'todo' ? node.open ? 'ready' : 'locked' : node.status; strip.append(button(`${node.title} · ${status}`, () => showNode(node, level))); }
    anytime.append(strip); root.append(anytime);
  }
  if (state.overview.mission?.pack_id) {
    const refs = await api(`lab-catalog?track=${encodeURIComponent(state.overview.mission.pack_id)}`);
    const section = trackLabReferences(refs); if (section) root.append(section);
  }
}

async function renderStats() {
  const [stats, days, levels, session, practice] = await Promise.all([api('stats'), api('heatmap'), api('levels'), command(['session', 'status']), api('playground/insights')]);
  const root = $('#stats-content'); root.replaceChildren();
  updateStreak(stats.current_streak);
  const summary = el('section', undefined, 'stats-summary'); summary.setAttribute('aria-label', 'Progress summary');
  const metrics = el('dl', undefined, 'metric-strip');
  for (const [value, label, unit, className] of [
    [stats.current_streak, 'Current streak', 'days', 'streak-number'],
    [stats.best_streak, 'Best streak', 'days', ''],
    [stats.minutes_this_week, 'This week', 'min', ''],
    [session.xp, 'Verified XP', 'XP', '']
  ]) {
    const metric = el('div'), valueNode = el('dd');
    valueNode.append(el('span', value.toLocaleString(), className), el('span', unit === 'days' && value === 1 ? 'day' : unit, 'metric-unit'));
    metric.append(el('dt', label), valueNode); metrics.append(metric);
  }
  const note = el('p', `${stats.freeze_available} ${stats.freeze_available === 1 ? 'freeze' : 'freezes'} available this week · ${session.verified_awards} verified ${session.verified_awards === 1 ? 'task' : 'tasks'}. `, 'small muted');
  const xpHelp = el('a', 'How XP works'); xpHelp.href = '#docs/timers'; note.append(xpHelp);
  summary.append(metrics, note); root.append(summary);
  root.append(el('p', `XP contributions: track ${stats.xp.track} · practice ${stats.xp.practice} · standalone challenges ${stats.xp.challenge}. Playground activity does not advance the path.`, 'muted'));
  root.append(el('p', `${stats.playground.practice_completed} practice exercises completed · ${stats.playground.challenges_solved} standalone challenges solved · ${stats.playground.saved_work} saved activities`, 'small'));
  const insights = el('details', undefined, 'pg-reference'); insights.append(el('summary', 'Practice over the last 14 days'), el('p', `${practice.resumed} activities resumed · ${practice.returned} returns to the track · ${practice.runs_with_hints} activities with hints · ${practice.revealed_runs} solution reviews`), el('p', `${practice.queries_with_ready_choices} of ${practice.selection_queries} observed filter selections offered a ready activity. ${practice.feedback_reports} feedback reports: ${practice.unclear_reports} unclear, ${practice.unwanted_repeats} unwanted repeats, ${practice.environment_issues} technical problems.`, 'small'), el('p', 'These are local usage observations, not measures of mastery. Time estimates stay authored until at least three clear, completed sessions provide personal pace data.', 'small muted')); root.append(insights);
  const plots = el('div', undefined, 'page-section stats-plots');
  const calendar = el('section'); calendar.append(el('h2', 'Your last 12 weeks'), el('p', 'Each square is a learning day.', 'muted small'));
  const calendarArea = el('div', undefined, 'stats-chart-area'), heat = el('div', undefined, 'heatmap');
  for (const day of days) { const cell = el("div", undefined, `heat-day${day.count ? " logged" : ""}`); cell.title = `${day.day}: ${day.count} entries`; cell.setAttribute("aria-label", cell.title); cell.setAttribute("role", "img"); heat.append(cell); }
  calendarArea.append(heat); calendar.append(calendarArea);
  const minutes = el('section'); minutes.append(el('h2', 'Time well spent'), el('p', 'Minutes logged each week.', 'muted small'));
  const minutesArea = el('div', undefined, 'stats-chart-area'), chart = el('div', undefined, 'weekly-chart');
  const max = Math.max(1, ...stats.weeks.map(week => week.minutes));
  for (const week of stats.weeks) {
    const item = el("div", undefined, "week");
    const bar = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    bar.setAttribute("viewBox", "0 0 40 120"); bar.setAttribute("width", "40"); bar.setAttribute("height", "120");
    bar.setAttribute("role", "img"); bar.setAttribute("aria-label", `${week.week}: ${week.minutes} minutes`);
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    const height = Math.max(2, week.minutes / max * 118);
    rect.setAttribute("x", "4"); rect.setAttribute("width", "32"); rect.setAttribute("y", String(120-height)); rect.setAttribute("height", String(height)); rect.setAttribute("rx", "5"); rect.setAttribute("fill", "currentColor");
    bar.append(rect); item.append(el("span", `${week.minutes}m`), bar, el("span", week.week.slice(5))); chart.append(item);
  }
  minutesArea.append(chart); minutes.append(minutesArea); plots.append(calendar, minutes); root.append(plots);
  const achievements = el("section", undefined, "page-section achievements");
  achievements.append(el("h2", "Milestones you've earned"));
  const earned = levels.flatMap(level => level.nodes).filter(node => node.milestone && node.status === "done");
  const shelf = el("div", undefined, "earned-milestones");
  for (const node of earned) { const badge = el("div", undefined, "earned-badge"); badge.append(icon("flag"), el("span", node.title.replace(/\s*\(milestone\)$/i, ""))); shelf.append(badge); }
  if (!earned.length) achievements.append(el("p", "Complete a milestone in your active track to add it here. Each one represents a skill you've put into practice.", "muted"));
  else achievements.append(shelf);
  root.append(achievements);
}
function updateStreak(days) {
  const previous = Number.parseInt($('#streak').textContent, 10);
  $('#streak').textContent = days;
  const label = `View streak stats: ${days} ${days === 1 ? 'day' : 'days'}`;
  $('#streak-link').setAttribute('aria-label', label);
  $('#streak-link').title = label;
  if (Number.isFinite(previous) && days > previous) window.AscendMotion?.feedback?.($('#streak-link'), 'streak');
}
function updateAccountChrome() {
  if (!state.account) return;
  $('#avatar-initial').textContent = state.account.username.slice(0, 1).toUpperCase();
  $('#profile-link').title = `${state.account.username} · Profile`;
}
async function refreshDocsChrome() {
  // Documentation remains readable when the account is offline or signed out.
  const [account, sessions, stats] = await Promise.all([
    api('account', undefined, 'GET', false),
    api('command', {argv: ['session', 'status']}, 'POST', false),
    api('stats', undefined, 'GET', false)
  ]);
  state.account = account;
  state.sessions = sessions; state.sessionFetched = performance.now();
  updateAccountChrome();
  updateStreak(stats.current_streak);
  $('#xp-balance').textContent = `${sessions.xp.toLocaleString()} XP`;
  $('#xp-link').setAttribute('aria-label', `${sessions.xp} verified XP. View progress`);
  renderSessionClock();
}
function bindAction(selector, action, after) { const node = $(selector); node.addEventListener('click', () => runAction(node, action, after)); }
function syncMissionActions() {
  const active = Boolean(state.overview?.mission);
  $('#start-mission').disabled = active || !state.installedPacks.some(pack => pack.id === $('#mission-pack').value);
  $('#pause-mission').disabled = !active;
  $('#finish-mission').disabled = !active;
  $('#save-mission-time').disabled = !active;
}
function packTitle(pack) { return pack.title || pack.id.replaceAll('-', ' '); }
const TRACK_DOMAINS = {
  Foundations: 'Cyber foundations',
  Offensive: 'Offensive security',
  Defensive: 'Defensive security',
  Engineering: 'Security engineering',
  Specialist: 'Specialist security',
  Practice: 'Hands-on labs',
  Projects: 'Projects',
  Custom: 'Custom tracks'
};
function packDomain(pack) { return pack.category || 'Custom'; }
function drawMissionTracks(selectedId = '') {
  const domain = $('#mission-domain').value, select = $('#mission-pack');
  const packs = state.installedPacks.filter(pack => packDomain(pack) === domain).sort((a, b) => packTitle(a).localeCompare(packTitle(b)));
  const placeholder = el('option', domain ? 'Choose a track…' : 'Choose a domain first'); placeholder.value = '';
  select.replaceChildren(placeholder, ...packs.map(pack => {
    const option = el('option', packTitle(pack)); option.value = pack.id; return option;
  }));
  select.value = packs.some(pack => pack.id === selectedId) ? selectedId : '';
  select.disabled = !packs.length;
  $('#mission-picker-help').textContent = !state.installedPacks.length ? 'No tracks installed yet. Browse learning tracks to get started.' : domain ? `${packs.length} installed ${packs.length === 1 ? 'track' : 'tracks'} in ${TRACK_DOMAINS[domain] || domain}.` : 'Pick a domain to see its tracks.';
  syncMissionActions();
}
function drawMissionPicker() {
  const select = $('#mission-domain'), previousDomain = select.value;
  const selected = state.installedPacks.find(pack => pack.id === $('#mission-pack').value)
    || (!previousDomain && state.installedPacks.find(pack => pack.id === state.overview?.mission?.pack_id));
  const counts = new Map();
  for (const pack of state.installedPacks) counts.set(packDomain(pack), (counts.get(packDomain(pack)) || 0) + 1);
  const domains = [...new Set([...Object.keys(TRACK_DOMAINS), ...counts.keys()])].filter(domain => counts.has(domain));
  const placeholder = el('option', domains.length ? 'Choose a domain…' : 'No installed tracks'); placeholder.value = '';
  select.replaceChildren(placeholder, ...domains.map(domain => {
    const option = el('option', `${TRACK_DOMAINS[domain] || domain} (${counts.get(domain)})`); option.value = domain; return option;
  }));
  select.value = selected ? packDomain(selected) : domains.includes(previousDomain) ? previousDomain : '';
  select.disabled = !domains.length;
  drawMissionTracks(selected?.id);
}
async function renderMore() {
  const [packs, parked, catalog] = await Promise.all([api('packs'), command(['parked']), command(['pack', 'registry'])]);
  // Older servers omit categories from installed packs. Resolve stable IDs
  // against the catalog so existing installations get the same domain picker.
  const domains = new Map(catalog.map(pack => [pack.id, pack.category || 'Projects']));
  state.installedPacks = packs.map(pack => ({...pack, category: domains.get(pack.id) || pack.category || 'Custom'}));
  $('#mission-name').textContent = state.overview?.mission?.title || 'No active mission';
  $('#mission-time').value = state.overview?.mission?.nudge_time || '';
  drawMissionPicker();
  drawInstalledPacks();
  $('#parked-list').replaceChildren(...parked.map(idea => {
    const item = el('li', idea.note);
    item.append(button('Resolve', async () => { await command(['resolve', String(idea.id)]); await renderMore(); }));
    return item;
  }));
}
function drawInstalledPacks() {
  const query = $('#installed-search').value.toLowerCase().trim();
  const packs = state.installedPacks.filter(pack => `${packTitle(pack)} ${pack.id}`.toLowerCase().includes(query));
  const shown = query || state.showAllPacks ? packs : packs.slice(0, 8);
  $('#pack-count').textContent = String(state.installedPacks.length);
  $('#pack-list').replaceChildren(...shown.map(pack => {
    const row = el('div', undefined, 'pack-item'); row.setAttribute('role', 'listitem');
    const copy = el('div', undefined, 'pack-copy');
    const title = el('span', packTitle(pack), 'pack-name'); title.title = packTitle(pack);
    const detail = pack.valid === false ? 'Needs attention · open for details' : `${pack.levels || 'Custom'} levels · ${pack.nodes || 'Custom'} tasks · ${pack.reviewed ? 'Reviewed' : 'Draft'}`;
    copy.append(title, el('p', detail, 'pack-meta'));
    const read = button('Read', () => readPack(pack), 'secondary pack-read');
    read.id = `read-pack-${pack.id}`;
    read.setAttribute('aria-label', `Read ${packTitle(pack)}`);
    read.prepend(icon('book'));
    row.append(copy, read); return row;
  }));
  if (!shown.length) $('#pack-list').append(el('p', query ? 'No installed packs match that search.' : 'Your library is empty. Browse tracks to find a starting point.', 'muted'));
  $('#show-all-packs').hidden = Boolean(query) || packs.length <= 8;
  $('#show-all-packs').textContent = state.showAllPacks ? 'Show fewer packs' : `Show all ${packs.length} packs`;
}
async function readPack(pack) {
  const data = await api(`packs/${pack.id}`);
  const content = openSheet('Track overview');
  const heading = el('h2', data.title); heading.id = 'sheet-title';
  content.append(heading, el('p', `${data.levels.filter(l => l.lane === 'main').length} levels · ${data.nodes.length} tasks · ${pack.reviewed ? 'Reviewed by you' : 'Draft — read before using'}`, 'muted'));
  const overview = el('div', undefined, 'pack-overview');
  data.levels.forEach((level, index) => {
    const group = el('details', undefined, 'pack-level'); group.open = index === 0;
    const nodes = data.nodes.filter(node => node.level === level.id);
    group.append(el('summary', `${level.title} · ${nodes.length} tasks`));
    const list = el('ul');
    nodes.forEach(node => { const item = el('li'); item.append(el('h3', node.title)); if (node.preview) item.append(el('p', node.preview)); list.append(item); });
    group.append(list); overview.append(group);
  });
  content.append(overview, el('p', 'This is the track overview. Detailed tasks open when their attempts start. Marking this overview reviewed does not complete lessons or enable command execution.', 'muted'));
  const actions = el('div', undefined, 'dialog-actions');
  const review = button(pack.reviewed ? 'Already reviewed' : 'Mark reviewed', async () => {
    await command(['pack', 'review', pack.id]); $('#sheet').close(); await renderMore(); document.getElementById(`read-pack-${pack.id}`)?.focus({preventScroll: true}); notify('Pack marked as reviewed.', 'success');
  });
  review.disabled = Boolean(pack.reviewed); actions.append(review); content.append(actions);
}
async function renderProfile() {
  const account = await api('account'); state.account = account; updateAccountChrome();
  await refreshSessions();
  const summary = $('#profile-summary'); summary.replaceChildren();
  const avatar = el('span', account.username.slice(0, 1).toUpperCase(), 'avatar'); avatar.setAttribute('aria-hidden', 'true');
  const identity = el('div', undefined, 'profile-identity');
  identity.append(el('h2', account.username), el('p', account.auth_mode === 'single' ? 'Local learning account' : 'Your learning account'));
  const metrics = el('div', undefined, 'profile-metrics');
  for (const [value, label] of [[state.sessions.xp, 'Verified XP'], [state.sessions.verified_awards, 'Verified tasks'], [state.overview?.current_streak || 0, 'Day streak']]) {
    const metric = el('div', undefined, 'profile-metric'); metric.append(el('strong', value.toLocaleString()), el('span', label)); metrics.append(metric);
  }
  summary.append(avatar, identity, metrics);
  $('#account-info').textContent = `${account.username} · ${location.origin}`;
  $('#account-timezone').value = account.timezone;
  if (!$('#timezone-options').children.length) {
    const zones = new Set(['UTC', 'Asia/Kolkata', 'Europe/London', 'America/New_York', account.timezone, ...(Intl.supportedValuesOf?.('timeZone') || [])]);
    for (const zone of [...zones].sort()) {
      const option = el('option'); option.value = zone;
      try {
        const offset = new Intl.DateTimeFormat('en', {timeZone: zone, timeZoneName: 'shortOffset'}).formatToParts().find(part => part.type === 'timeZoneName').value.replace('GMT', 'UTC');
        option.label = `${zone === 'Asia/Kolkata' ? 'India · ' : ''}${zone.replaceAll('_', ' ')} · ${offset}`;
      } catch { option.label = zone; }
      $('#timezone-options').append(option);
    }
  }
  $('#nudge-time').value = account.settings.nudge_time || '21:30';
  $('#nudge-channel').value = account.settings.nudge_channel || 'ntfy';
  $('#ntfy-topic').value = account.settings.ntfy_topic || '';
  $('#nudge-enabled').checked = account.settings.nudge_enabled || false;
  $('#logout').hidden = account.auth_mode === 'single';
  $('#public-streak').checked = account.settings.public_streak || false;
  $('#public-link').textContent = account.settings.public_streak ? `${location.origin}/api/public/${encodeURIComponent(account.username)}/badge.svg` : 'Your streak is private. Sharing is optional.';
}
document.querySelectorAll("[data-icon]").forEach(node => node.append(icon(node.dataset.icon)));
window.addEventListener('hashchange', () => {
  const {tab, topic} = currentRoute();
  if ($('#sheet').open) $('#sheet').close();
  if (tab !== state.tab || (tab === 'attempts' && topic && decodeURIComponent(topic) !== state.attemptGroupRef) || (tab === 'lab' && topic && decodeURIComponent(topic) !== state.labRef) || (tab === 'docs' && topic && topic !== state.guideTopic) || (tab === 'playground' && topic && topic !== state.playgroundRoute) || (tab === 'activity' && topic && topic !== state.activityRef) || (tab === 'challenge' && topic && decodeURIComponent(topic) !== state.challengeRef)) switchTab(tab, {topic}).catch(error => notify(error.message, 'error'));
});
$("#jump-current").addEventListener("click", () => jumpToLevel(currentLevel()?.id));
document.querySelectorAll("[data-tab]").forEach(node => node.addEventListener("click", () => switchTab(node.dataset.tab).catch(error => notify(error.message, 'error'))));
$("#streak-link").addEventListener("click", () => switchTab("stats").catch(error => notify(error.message, 'error')));
document.querySelectorAll("[data-minutes]").forEach(node => node.addEventListener("click", async () => { state.minutes = node.dataset.minutes || null; document.querySelectorAll("[data-minutes]").forEach(chip => chip.setAttribute("aria-pressed", String(chip === node))); try { await refresh(); } catch (error) { notify(error.message, 'error'); } }));
$('#sheet .close').addEventListener('click', () => $('#sheet').close());
$('#notice button').addEventListener('click', dismissNotice);
for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('close', () => {
  if (dialog.contains($('#notice'))) { dismissNotice(); document.body.append($('#notice')); }
});
$('#xp-link').addEventListener('click', () => switchTab('stats').catch(error => notify(error.message, 'error')));
$('#profile-link').addEventListener('click', () => switchTab('profile').catch(error => notify(error.message, 'error')));
$('#installed-search').addEventListener('input', drawInstalledPacks);
$('#show-all-packs').addEventListener('click', () => { state.showAllPacks = !state.showAllPacks; drawInstalledPacks(); });
$('#mission-domain').addEventListener('change', () => drawMissionTracks());
$('#mission-pack').addEventListener('change', syncMissionActions);
$("#sheet").addEventListener("click", event => { if (event.target === $("#sheet")) { const box = event.target.getBoundingClientRect(); if (event.clientY < box.top || event.clientY > box.bottom || event.clientX < box.left || event.clientX > box.right) event.target.close(); } });
function handleForm(selector, handler) {
  $(selector).addEventListener('submit', event => {
    event.preventDefault();
    const submit = event.submitter || $('button[type="submit"], button:not([type])', event.target);
    runAction(submit, () => handler(event));
  });
}
handleForm("#search-form", async () => { const results = await api(`search?q=${encodeURIComponent($("#search").value)}`); $("#search-results").replaceChildren(...results.map(entry => { const item = el("article", undefined, "search-result"); item.append(el("p", entry.learned), el("p", `${entry.day} · ${entry.node_id || "Personal note"}`, "muted")); return item; })); if (!results.length) $("#search-results").append(el("p", "No matching notes yet.", "muted")); });
handleForm("#install-form", async () => { await command(["pack", "install", $("#pack-id").value]); await renderMore(); notify("Pack installed. Read it before trusting its checks."); });
$("#pack-upload").addEventListener("change", async event => { if (!event.target.files[0]) return; const data = new FormData(); data.append("file", event.target.files[0]); try { await api("packs", data); await renderMore(); notify("Pack installed."); } catch (error) { notify(error.message, 'error'); } });
bindAction('#start-mission', async () => {
  const args = ['mission', 'start', $('#mission-pack').value];
  if ($('#mission-time').value) args.push('--nudge-time', $('#mission-time').value);
  await command(args); await refresh(); await renderMore(); notify('Mission started.', 'success');
}, syncMissionActions);
for (const action of ['pause', 'finish']) bindAction(`#${action}-mission`, async () => {
  await command(['mission', action]); await refresh(); await renderMore(); notify(action === 'pause' ? 'Mission paused. Your progress is saved.' : 'Mission finished.', 'success');
}, syncMissionActions);
bindAction('#save-mission-time', async () => {
  await command(['mission', 'nudge-time', $('#mission-time').value || 'off']); await refresh(); notify('Mission reminder saved.', 'success');
}, syncMissionActions);
handleForm('#reminder-form', async () => {
  await command(['config', 'nudge-time', $('#nudge-time').value]);
  await command(['config', 'nudge-channel', $('#nudge-channel').value]);
  await command(['config', 'ntfy-topic', $('#ntfy-topic').value]);
  await command(['config', 'nudge-enabled', String($('#nudge-enabled').checked)]);
  notify('Reminders saved.', 'success');
});
bindAction('#test-nudge', async () => { const result = await command(['config', 'nudge-test']); notify(result.sent ? 'Test reminder sent.' : result.reason, result.sent ? 'success' : 'error'); });
handleForm('#park-form', async () => { await command(['park', $('#park-note').value]); $('#park-note').value = ''; await renderMore(); notify('Idea saved for later.', 'success'); });
bindAction('#save-timezone', async () => { await command(['config', 'timezone', $('#account-timezone').value]); await refresh(); notify('Timezone saved.', 'success'); });
function setTheme(theme) { if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme; localStorage.setItem("ascend-theme", theme); }
$("#theme").value = localStorage.getItem("ascend-theme") || "system"; setTheme($("#theme").value);
$("#theme").addEventListener("change", event => setTheme(event.target.value));
$("#logout").addEventListener("click", async () => { try { await api("logout", {}); sessionStorage.removeItem("ascend-token"); state.token = null; location.reload(); } catch (error) { notify(error.message, 'error'); } });
$("#public-streak").addEventListener("change", async event => { try { await command(["config", "public-streak", String(event.target.checked)]); await renderProfile(); } catch (error) { notify(error.message, 'error'); } });
$("#enable-push").addEventListener("click", async () => {
  try {
    if (!("Notification" in window) || !("PushManager" in window) || !window.isSecureContext) throw new Error("Browser notifications require HTTPS and a supported browser.");
    if (await Notification.requestPermission() !== "granted") throw new Error("Notification permission was not granted.");
    const {public_key} = await api("push/key");
    const raw = atob(public_key.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4-public_key.length%4)%4));
    const key = Uint8Array.from(raw, character => character.charCodeAt(0));
    const worker = await navigator.serviceWorker.ready;
    const subscription = await worker.pushManager.getSubscription() || await worker.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: key});
    await api("push/subscriptions", subscription.toJSON());
    await command(["config", "nudge-channel", "webpush"]);
    $("#nudge-channel").value = "webpush";
    $("#push-status").textContent = "This browser is subscribed. Enable reminders and send a test when ready.";
  } catch (error) { $("#push-status").textContent = error.message; }
});
$("#disable-push").addEventListener("click", async () => {
  try {
    if (!("serviceWorker" in navigator)) throw new Error("This browser does not support notifications.");
    const worker = await navigator.serviceWorker.ready;
    const subscription = await worker.pushManager.getSubscription();
    if (subscription) { await api("push/subscriptions", {endpoint: subscription.endpoint}, "DELETE"); await subscription.unsubscribe(); }
    $("#push-status").textContent = "Notifications are disabled on this browser.";
  } catch (error) { $("#push-status").textContent = error.message; }
});
handleForm("#login-form", async () => { try { const result = await api("login", {username: $("#username").value, password: $("#password").value}); state.token = result.token; sessionStorage.setItem("ascend-token", result.token); $("#password").value = ""; $("#login-dialog").close(); await refresh(); await switchTab(state.tab); } catch (error) { $("#login-error").textContent = error.message; } });
document.addEventListener("keydown", event => { if (event.key.toLowerCase() === "l" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) && !$("#sheet").open && state.overview?.next) openLog(state.overview.next); });
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
const initialRoute = currentRoute();
switchTab(initialRoute.tab, {topic: initialRoute.topic}).catch(error => notify(error.message, 'error')).finally(() => {
  window.AscendBoot?.finish();
  playChallengeIntro();
});

// Timers are scored by the server; this display is only a synchronized preview.
async function refreshSessions() {
  state.sessions = await command(['session', 'status']);
  state.sessionFetched = performance.now();
  $('#xp-balance').textContent = `${state.sessions.xp.toLocaleString()} XP`;
  $('#xp-link').setAttribute('aria-label', `${state.sessions.xp} verified XP. View progress`);
  const current = [state.sessions.active, ...state.sessions.paused].filter(Boolean);
  document.querySelectorAll('button[data-challenge]').forEach(node => {
    const label = current.some(item => `${item.pack_id}:${item.node_id}` === node.dataset.challenge) ? 'Resume challenge' : node.dataset.defaultLabel;
    if (node.textContent !== label) node.replaceChildren(document.createTextNode(label), icon('arrow'));
  });
  renderSessionClock();
}
function renderSessionClock() {
  const root = $('#task-session'); if (!root || !state.sessions) return;
  const lab = state.sessions.local_lab_active;
  if (lab) {
    const key = `local-lab-${lab.id}`;
    root.hidden = false; root.dataset.state = 'running';
    if (root.dataset.session !== key) {
      root.dataset.session = key; root.replaceChildren(el('span', 'Local lab', 'session-label'), el('strong', lab.recipe_id), sessionButton('View lab session', 'View lab', () => playgroundOpen('labs'), ''));
    }
    return;
  }
  const current = state.sessions.active;
  if (state.tab === 'activity' && !current) { root.hidden = true; delete root.dataset.session; return; }
  const recent = state.sessions.recent;
  const renderKey = `${state.tab}:${state.challengeRef || ''}:` + (current ? `active-${current.id}` : `paused-${state.sessions.paused.map(r => r.id).join('-')}:recent-${recent?.id}-${recent?.outcome}`);
  const changed = root.dataset.session !== renderKey;
  if (changed) { root.replaceChildren(); root.dataset.session = renderKey; }
  root.hidden = !current && !state.sessions.paused.length;
  root.dataset.state = current ? 'running' : 'finished';
  if (current) {
    const elapsed = current.elapsed_seconds + Math.floor((performance.now() - state.sessionFetched) / 1000);
    const remaining = Math.max(0, current.budget_seconds - elapsed);
    if (changed) {
      const title = el('strong', compactTitle(current.title)); title.title = current.title;
      const clock = el('span', undefined, 'session-clock');
      clock.append(el('span', '', 'clock-value'), el('small', 'elapsed / target', 'clock-caption'));
      root.append(el('span', current.practice ? 'Practice' : 'In progress', 'session-label'), title, clock);
      const ref = `${current.pack_id}:${current.node_id}`;
      if (state.tab !== 'challenge' || state.challengeRef !== ref) root.append(sessionButton('Resume challenge', 'Resume', () => switchTab('challenge', {topic: ref}), ''));
      root.append(sessionButton('Finish session', 'Finish', endTaskSession, 'secondary'));
    }
    const clock = root.querySelector('.session-clock');
    clock.querySelector('.clock-value').textContent = `${formatTime(elapsed)} / ${formatTime(current.budget_seconds)}`;
    clock.querySelector('.clock-caption').textContent = remaining ? 'elapsed / target' : 'elapsed / target · overtime';
    const checkpoint = elapsed >= current.budget_seconds ? 2 : elapsed >= current.budget_seconds * .75 ? 1 : 0;
    const key = `ascend-session-notice-${current.id}-${current.running_since}`;
    if (checkpoint > Number(sessionStorage.getItem(key) || 0)) {
      sessionStorage.setItem(key, String(checkpoint));
      notify(checkpoint === 2 ? 'Your target time has elapsed. Verified completion still earns XP.' : 'Three quarters of your planned session has elapsed.', 'reminder');
    }
  } else if (changed && state.sessions.paused.length) {
    const saved = state.sessions.paused[state.sessions.paused.length - 1];
    const ref = `${saved.pack_id}:${saved.node_id}`;
    root.append(el('strong', `Previous session: ${saved.title}`));
    if (state.tab !== 'challenge' || state.challengeRef !== ref) root.append(button('Resume challenge', () => switchTab('challenge', {topic: ref}), ''));
    root.append(button('Finish session', endTaskSession, 'secondary'));

  }
}
function sessionButton(label, compact, action, className) {
  const node = button(label, action, className); node.setAttribute('aria-label', label);
  node.replaceChildren(el('span', label, 'session-action-long'), el('span', compact, 'session-action-short'));
  return node;
}
function formatTime(seconds) { return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds) % 60).padStart(2, '0')}`; }
async function endTaskSession() {
  await prepareToEndChallenge();
}
function verificationLabel(node) {
  return node.verify?.type === 'lab' ? (node.verify.exercise === 'case' ? 'Server-graded reasoning check' : 'Server-verified exercise') : node.verify?.type === 'ctf' ? 'Signed external lab evidence' : node.verify?.type === 'file' ? 'Artifact check · reasoning needs review' : 'Evidence review required';
}
async function renderChallenge() {
  try { await flushChallengeNotebook(); } catch { /* Draft recovery stays available. */ }
  activeNotebook = null;
  const saved = state.sessions?.active || state.sessions?.paused.at(-1);
  const ref = state.challengeRef || (saved ? `${saved.pack_id}:${saved.node_id}` : null);
  const content = $('#challenge-content');
  const heading = el('h1', 'Your challenge'); heading.id = 'challenge-title'; heading.tabIndex = -1;
  content.replaceChildren(heading, el('p', ref ? 'Opening your workspace…' : 'Choose a challenge from Today or your learning path.', 'muted'));
  if (!ref) return;
  state.challengeRef = ref;
  history.replaceState(null, '', `#challenge/${encodeURIComponent(ref)}`);
  try {
    const data = await api(`challenges/${encodeURIComponent(ref)}`);
    if (state.tab !== 'challenge' || state.challengeRef !== ref) return;
    document.title = `${data.node.title} · Ascend`;
    if (data.exercise) showLab(data.node, data.exercise);
    else {
      showNode(data.node, data.level, true, data.session);
      if (data.exercise_error) content.append(el('p', data.exercise_error, 'error'));
      if (data.node.verify?.type === 'lab' && data.session) content.append(button(data.exercise_error ? 'Start a new exercise' : 'Open exercise', async () => {
        await command(['lab', 'start', ref]); await refreshSessions(); await renderChallenge();
      }, ''));
    }
    mountChallengeNotebook(data);
    $('#challenge-title').tabIndex = -1;
  } catch (error) {
    content.replaceChildren(heading, el('p', error.message, 'error'), button('Try again', renderChallenge));
  }
}
function showLab(node, run) {
  if (run.exercise === 'case') { showCase(node, run); return; }
  const policy = run.exercise === 'access-policy';
  const terminal = run.terminal || run.passed;
  const content = $('#challenge-content'); content.replaceChildren();
  const heading = el('h1', node.title); heading.id = 'challenge-title'; heading.tabIndex = -1;
  const instructions = policy ? run.instructions.replace('Return a boolean decision for every request.', 'Choose Allow or Deny for each request below.') : run.instructions;
  content.append(el('p', verificationLabel(node), 'eyebrow'), heading, el('p', instructions, 'challenge-brief'));
  if (run.marker) content.append(el('p', `Your exercise marker: ${run.marker}`));
  const workspace = el('div', undefined, `exercise-workspace${policy ? ' policy-workspace' : ''}`);
  const evidence = el('section', undefined, 'exercise-evidence'); evidence.append(el('h2', 'Exercise data'));
  const response = el('section', undefined, 'exercise-response'); response.append(el('h2', 'Your result'));
  if (!policy) workspace.append(evidence);
  workspace.append(response); content.append(workspace);
  const dataView = el('pre', JSON.stringify(run.data || {}, null, 2), 'lab-data');
  dataView.tabIndex = 0; dataView.setAttribute('aria-label', 'Exercise data');
  if (run.exercise === 'logging' && !run.passed) {
    const actions = el('div', undefined, 'input-row');
    for (const kind of ['ok', 'error']) actions.append(button(kind === 'ok' ? 'Send successful request' : 'Send failed request', async () => {
      Object.assign(run, await command(['lab', 'emit', run.id, kind]));
      dataView.textContent = JSON.stringify(run.data, null, 2);
    }));
    evidence.append(actions);
  }
  if (policy) {
    const raw = el('details', undefined, 'quiet-details'); raw.append(el('summary', 'View raw request data'), dataView); content.append(raw);
    response.querySelector('h2').textContent = 'Decide each request';
    if (terminal && run.score) {
      const title = response.querySelector('h2'); title.id = 'policy-result'; title.tabIndex = -1;
      title.textContent = `${run.score.correct} of ${run.score.total} correct · +${run.score.xp} XP`;
      response.append(el('p', run.passed ? 'Verified. Every decision is correct.' : 'Your submission is final. Review the rules below; this task is not fully complete.', 'field-help'));
      response.append(el('p', run.reward_eligible ? 'XP = time-based reward × correct decisions ÷ total, rounded down.' : 'This session ended before scoring, so no XP was awarded.', 'field-help'));
    } else response.append(el('p', 'One submission. Correct decisions earn equal shares of XP; incorrect decisions earn none.', 'field-help'));
  } else if (Object.keys(run.data || {}).length) evidence.append(dataView);
  else evidence.append(el('p', 'Use the scenario above to make your decision.', 'muted'));
  if (run.passed && !policy) response.append(el('p', '✓ This instance has passed. Repeating it does not award XP again.', 'success-note'));
  const draftKey = `ascend-answer-${state.account?.username || 'local'}-${run.id}`;
  let draft = {};
  try { draft = JSON.parse(sessionStorage.getItem(draftKey) || '{}'); } catch { /* Empty draft. */ }
  const form = el('form'); const inputs = {};
  for (const [key, value] of Object.entries(run.answer_template)) {
    if (typeof value === 'boolean') {
      const group = el('fieldset', undefined, 'decision-field');
      group.append(el('legend', policy ? `Request ${key}` : key.replaceAll('_', ' ')));
      const row = el('div', undefined, 'decision-row');
      const request = policy && run.data?.requests?.find(item => item.id === key);
      if (request) {
        const context = el('div', undefined, 'decision-context');
        const titleCase = text => text.charAt(0).toUpperCase() + text.slice(1);
        context.append(el('p', `${titleCase(request.action)} · ${titleCase(request.role)} · ${request.enabled ? 'Enabled' : 'Disabled'}`));
        context.append(el('p', request.caller === request.owner ? 'Caller owns this object' : 'Caller does not own this object', 'muted small'));
        row.append(context);
      }
      const choices = el('div', undefined, 'decision-choices');
      const feedback = policy && run.feedback?.find(item => item.id === key);
      if (terminal && feedback) {
        if (feedback.correct !== null) group.dataset.correct = feedback.correct;
        const outcome = el('div', undefined, 'decision-outcome');
        const decision = feedback.allowed ? 'Allow' : 'Deny';
        outcome.append(el('strong', `${feedback.correct === null ? 'Decision' : feedback.correct ? 'Correct' : 'Incorrect'} · ${decision}`));
        if (feedback.selected !== null) outcome.append(el('span', `You chose ${feedback.selected ? 'Allow' : 'Deny'}`, 'muted small'));
        choices.append(outcome);
      } else for (const [answer, text] of [[true, policy ? 'Allow' : 'Yes'], [false, policy ? 'Deny' : 'No']]) {
        const option = el('input'); option.type = 'radio'; option.name = `lab-answer-${key}`; option.value = String(answer); option.required = true; option.disabled = terminal;
        option.checked = draft[key] === answer;
        const label = el('label', undefined, 'decision-choice'); label.append(option, el('span', text)); choices.append(label);
      }
      row.append(choices); group.append(row);
      if (terminal && feedback) group.append(el('p', feedback.explanation, 'decision-explanation'));
      form.append(group); inputs[key] = {type: 'boolean', input: group}; continue;
    }
    const label = el('label', key.replaceAll('_', ' ')); label.htmlFor = `lab-answer-${key}`;
    const input = el('input'); input.type = typeof value === 'number' ? 'number' : 'text';
    input.id = `lab-answer-${key}`; input.required = true; input.disabled = run.passed;
    input.value = draft[key] ?? '';
    const field = el('div', undefined, 'exercise-field'); field.append(label, input);
    inputs[key] = {input, type: typeof value}; form.append(field);
  }
  const result = el('p'); result.setAttribute('role', 'status');
  const submit = el('button', policy ? 'Submit decisions' : 'Verify my result'); submit.type = 'submit'; submit.disabled = terminal;
  const actions = el('div', undefined, 'exercise-actions');
  if (policy && terminal) actions.append(button(run.passed ? 'Continue learning' : 'Continue with partial result', async () => {
    if (!run.passed && node.status === 'todo') await api(`nodes/${node.pack_id}:${node.id}/mark`, {status: 'skipped'});
    await refresh(); await switchTab('today');
  }, ''));
  else actions.append(submit);
  form.append(actions, result); response.append(form);
  function answers() {
    return Object.fromEntries(Object.entries(inputs).flatMap(([key, entry]) => {
      if (entry.type === 'boolean') {
        const selected = entry.input.querySelector(':checked');
        return selected ? [[key, selected.value === 'true']] : [];
      }
      return [[key, entry.type === 'number' ? Number(entry.input.value) : entry.input.value.trim()]];
    }));
  }
  form.addEventListener('input', () => { try { sessionStorage.setItem(draftKey, JSON.stringify(answers())); } catch { /* Server exercise data remains saved. */ } });
  form.addEventListener('submit', async event => {
    event.preventDefault(); submit.disabled = true;
    try {
      const checked = await command(['lab', 'submit', run.id, JSON.stringify(answers())]);
      if (policy && checked.exercise?.terminal) {
        try { sessionStorage.removeItem(draftKey); } catch { /* No stored draft. */ }
        await refresh(); await refreshSessions();
        if (state.tab === 'challenge' && state.challengeRef === `${node.pack_id}:${node.id}`) {
          await renderChallenge(); $('#policy-result')?.focus();
          if (checked.completed) showChallengeCelebration('Decisions complete!', 'Your result is recorded and your track is ready for the next step.');
        }
        return;
      }
      result.textContent = checked.summary;
      if (checked.completed) {
        const gained = (checked.timer?.xp || 0) - (run.timer?.xp || 0);
        result.textContent = `✓ Verified.${gained > 0 ? ` +${gained} XP.` : ''} ${run.exercise === 'case' ? 'Your scenario decision passed; the hands-on assessment remains separate.' : 'The server recorded the demonstrated result.'}`;
        form.querySelectorAll('input, button').forEach(input => input.disabled = true);
        try { sessionStorage.removeItem(draftKey); } catch { /* No stored draft. */ }
        await refresh(); await refreshSessions();
        if (state.tab === 'path') await renderPath();
        if (state.tab === 'challenge') showChallengeCelebration('Challenge complete!', `${gained > 0 ? `+${gained} XP earned. ` : ''}Your evidence is recorded. Continue with the next task.`);
      } else submit.disabled = false;
    } catch (error) { result.textContent = error.message; submit.disabled = false; }
  });
  const reset = el('details', undefined, 'quiet-details'); reset.append(el('summary', 'Exercise options'), el('p', 'A fresh instance replaces the exercise data and clears your draft answers. The original timer target is preserved.', 'muted small'));
  reset.append(button('Start a fresh exercise instance', async () => {
    await command(['lab', 'start', `${node.pack_id}:${node.id}`, '--fresh']);
    try { sessionStorage.removeItem(draftKey); } catch { /* No stored draft. */ }
    await refreshSessions(); await renderChallenge();
  }));
  if (!policy) content.append(reset);
}
function showCase(node, run) {
  const content = $('#challenge-content'); content.replaceChildren();
  const column = el('div', undefined, 'case-workspace'); content.append(column);
  const terminal = run.terminal || run.passed;
  const heading = el('h1', run.title && run.title !== 'Make the call' ? run.title : compactTitle(node.title)); heading.id = 'challenge-title'; heading.tabIndex = -1;
  column.append(el('p', 'KNOWLEDGE CHECK', 'eyebrow'), heading, el('p', run.instructions, 'case-scenario'));
  const form = el('form'), group = el('fieldset');
  group.append(el('legend', run.question || 'What should you conclude or do next?'));
  const draftKey = `ascend-answer-${state.account?.username || 'local'}-${run.id}`;
  let selected = run.feedback?.selected || (run.passed ? run.feedback?.correct_choice : null);
  if (!terminal) { try { selected = JSON.parse(sessionStorage.getItem(draftKey) || '{}').choice; } catch { /* Empty draft. */ } }
  for (const [id, text] of Object.entries(run.choices)) {
    const option = el('input'); option.type = 'radio'; option.name = 'case-choice'; option.value = id; option.required = true; option.disabled = terminal; option.checked = selected === id;
    const label = el('label', undefined, 'case-choice');
    const copy = el('span', text);
    if (terminal && run.feedback) {
      const notes = [];
      if (id === run.feedback.correct_choice) { label.classList.add('answer-correct'); notes.push('Best answer'); }
      if (id === run.feedback.selected) notes.push('Your answer');
      if (notes.length) copy.append(el('small', notes.join(' · '), 'answer-note'));
    }
    label.append(option, copy); group.append(label);
  }
  form.append(group); column.append(form);
  const status = el('div', undefined, 'case-feedback'); status.setAttribute('role', 'status');
  if (terminal) {
    status.dataset.feedback = run.passed ? 'success' : 'warning';
    status.append(el('h2', run.passed ? 'Correct. Check complete.' : 'Answer recorded. No XP earned.'));
    if (run.feedback?.explanation) status.append(el('p', run.feedback.explanation));
    status.append(button(run.passed ? 'Continue learning' : 'Continue without XP', async () => {
      if (!run.passed && node.status === 'todo') await api(`nodes/${node.pack_id}:${node.id}/mark`, {status: 'skipped'});
      await refresh(); await switchTab('today');
    }, ''));
    column.append(status);
  } else {
    form.append(el('p', 'One submission. Review your choice before sending.', 'field-help'));
    const submit = el('button', 'Submit answer'); submit.type = 'submit'; form.append(submit, status);
    form.addEventListener('input', () => { try { sessionStorage.setItem(draftKey, JSON.stringify({choice: group.querySelector(':checked')?.value})); } catch { /* Draft is optional. */ } });
    form.addEventListener('submit', event => {
      event.preventDefault();
      runAction(submit, async () => {
        const checked = await command(['lab', 'submit', run.id, JSON.stringify({choice: group.querySelector(':checked')?.value})]);
        try { sessionStorage.removeItem(draftKey); } catch { /* No saved draft. */ }
        await refresh();
        if (state.tab === 'challenge' && state.challengeRef === `${node.pack_id}:${node.id}`) {
          await renderChallenge();
          const feedback = $('.case-feedback');
          feedback?.scrollIntoView({block: 'nearest', behavior: 'instant'});
          if (feedback) { feedback.tabIndex = -1; feedback.focus({preventScroll: true}); }
        }
        if (checked.completed) showChallengeCelebration('Knowledge check complete!', 'Your answer is recorded. Continue with the next task.');
        if (!checked.terminal && !checked.completed) status.textContent = checked.summary;
      });
    });
  }
  const notes = el('details', undefined, 'quiet-details'); notes.append(el('summary', 'Review the lesson'));
  if (node.brief) notes.append(el('p', node.brief));
  if (node.resource) { const resource = el('a', `${node.resource_label || 'Learning reference'} ↗`); resource.href = node.resource; resource.target = '_blank'; resource.rel = 'noopener noreferrer'; notes.append(resource); }
  if (node.resource_note) notes.append(el('p', node.resource_note, 'field-help'));
  column.append(notes);
}
async function browseTracks() {
  const [catalog, installed, labs] = await Promise.all([command(['pack', 'registry']), api('packs'), api('lab-catalog')]);
  const installedIds = new Set(installed.map(p => p.id));
  const content = openSheet('Track catalog'), title = el('h2', 'Find your next track'); title.id = 'sheet-title';
  content.append(title, el('p', 'Explore a subject or role. Installing a track keeps your current mission in place.', 'muted'));
  const controls = el('div', undefined, 'catalog-controls');
  const searchGroup = el('div');
  const search = field(searchGroup, 'catalog-search', 'Search subjects and roles', 'search'); search.placeholder = 'SOC, red team, cloud…';
  const filter = el('select'); filter.setAttribute('aria-label', 'Track category');
  for (const group of ['All subjects', ...new Set(catalog.map(p => p.category || 'Projects'))]) { const option = el('option', group); option.value = group; filter.append(option); }
  controls.append(searchGroup, filter);
  const count = el('p', '', 'muted'), list = el('div', undefined, 'catalog-results'); content.append(controls, count, list);
  function draw() {
    const query = search.value.toLowerCase().trim();
    const matches = catalog.filter(p => (filter.value === 'All subjects' || (p.category || 'Projects') === filter.value) && [p.title, p.id, ...(p.aliases || [])].join(' ').toLowerCase().includes(query));
    count.textContent = `${matches.length} tracks · supplied curricula are drafts`; list.replaceChildren();
    for (const pack of matches) {
      const card = el('article', undefined, 'catalog-card'), row = el('div', undefined, 'catalog-row'), copy = el('div', undefined, 'catalog-copy');
      copy.append(el('p', pack.category || 'Project', 'eyebrow'), el('h3', pack.title));
      if (pack.main_levels) copy.append(el('p', `${pack.main_levels} levels · ${pack.nodes} tasks`, 'muted'));
      const install = button(installedIds.has(pack.id) ? 'Installed' : 'Install', async () => {
        await command(['pack', 'install', pack.id]); installedIds.add(pack.id); await renderMore(); draw(); notify('Track installed. Your current mission is unchanged.', 'success');
      });
      install.setAttribute('aria-label', installedIds.has(pack.id) ? `${pack.title} is installed` : `Install ${pack.title}`);
      install.disabled = installedIds.has(pack.id); row.append(copy, install); card.append(row);
      if (pack.entry || pack.limits) {
        const details = el('details'); details.append(el('summary', 'Entry skills & environment'));
        if (pack.entry) details.append(el('p', pack.entry));
        if (pack.limits) details.append(el('p', pack.limits));
        card.append(details);
      }
      const references = trackLabReferences(labs.filter(lab => lab.track_ids.includes(pack.id)));
      if (references) card.append(references);
      list.append(card);
    }
    if (!matches.length) list.append(el('p', 'No tracks match. Try a broader subject or choose All subjects.', 'muted'));
  }
  search.addEventListener('input', draw); filter.addEventListener('change', draw); draw();
}
$('#browse-tracks').addEventListener('click', () => runAction($('#browse-tracks'), browseTracks));
setInterval(renderSessionClock, 1000);
setInterval(() => { if (state.overview && !document.hidden && !$('#login-dialog').open) refreshSessions().catch(() => {}); }, 30000);

async function renderDocs() {
  if (!state.guides) {
    $('#docs-status').textContent = 'Loading the guide…';
    try {
      const response = await fetch('/guide.json');
      if (!response.ok) throw new Error('The guide could not load. Reload when you are connected.');
      state.guides = (await response.json()).topics;
    } catch (error) {
      $('#docs-status').textContent = error.message;
      const heading = el('h1', 'The guide is unavailable'); heading.id = 'guide-title';
      $('#docs-article').replaceChildren(heading, el('p', 'Reconnect and reload to download the guide for this browser.'));
      return;
    }
  }
  if (!state.guides.some(topic => topic.id === state.guideTopic)) state.guideTopic = 'getting-started';
  drawDocsTopics();
  const topic = state.guides.find(topic => topic.id === state.guideTopic);
  const article = $('#docs-article'); article.replaceChildren();
  document.title = `${topic.title} · Ascend Docs`;
  const heading = el('h1', topic.title); heading.id = 'guide-title'; heading.tabIndex = -1;
  article.append(el('p', topic.section || 'Documentation', 'eyebrow'), heading, el('p', topic.summary, 'guide-summary'));
  for (const block of topic.blocks) {
    if (block.type === 'paragraph') article.append(el('p', block.text));
    if (block.type === 'heading') article.append(el('h2', block.text));
    if (block.type === 'steps' || block.type === 'list') {
      const list = el(block.type === 'steps' ? 'ol' : 'ul');
      block.items.forEach(item => list.append(el('li', item))); article.append(list);
    }
    if (block.type === 'code') article.append(codeBlock(block.text));
  }
  const related = el('div', undefined, 'guide-next'); related.append(el('h2', 'Keep reading'));
  const links = el('div', undefined, 'guide-links');
  topic.related.forEach(id => {
    const next = state.guides.find(item => item.id === id);
    if (next) { const link = el('a', next.title); link.href = `#docs/${id}`; links.append(link); }
  });
  related.append(links); article.append(related);
}
function drawDocsTopics() {
  if (!state.guides) return;
  const query = $('#docs-search').value.trim().toLowerCase();
  const matching = state.guides.filter(topic => [topic.title, topic.summary, ...topic.blocks.map(block => block.text || block.items.join(' '))].join(' ').toLowerCase().includes(query));
  $('#docs-status').textContent = query ? `${matching.length} ${matching.length === 1 ? 'guide matches' : 'guides match'}` : '';
  const groups = new Map();
  for (const topic of matching) {
    const name = topic.section || 'Guides';
    if (!groups.has(name)) {
      const group = el('div', undefined, 'docs-topic-group');
      group.append(el('h3', name)); groups.set(name, group);
    }
    const item = el('a', topic.title); item.href = `#docs/${topic.id}`;
    item.addEventListener('click', async event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      try {
        $('#docs-search').value = '';
        await switchTab('docs', {topic: topic.id});
        $('#guide-title').focus({preventScroll: true});
        window.scrollTo({top: 0, behavior: 'instant'});
      } catch (error) { notify(error.message, 'error'); }
    });
    if (topic.id === state.guideTopic) item.setAttribute('aria-current', 'page');
    groups.get(name).append(item);
  }
  $('#docs-topics').replaceChildren(...groups.values());
  if (!matching.length) $('#docs-topics').append(el('p', 'No guide matches. Try “XP”, “packs”, or “Docker”.', 'muted small'));
}
$('#docs-toggle').addEventListener('click', () => {
  $('#docs-menu-body').append($('#docs-navigation'));
  document.documentElement.classList.add('docs-menu-open');
  $('#docs-menu').showModal();
  $('#docs-toggle').setAttribute('aria-expanded', 'true');
  $('#docs-search').focus({preventScroll: true});
});
$('#docs-close').addEventListener('click', () => $('#docs-menu').close());
$('#docs-menu').addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    event.preventDefault(); event.stopPropagation(); $('#docs-menu').close();
  }
});
$('#docs-menu').addEventListener('close', () => {
  $('#docs-sidebar-slot').append($('#docs-navigation'));
  document.documentElement.classList.remove('docs-menu-open');
  $('#docs-toggle').setAttribute('aria-expanded', 'false');
});
$('#docs-menu').addEventListener('click', event => {
  if (event.target === event.currentTarget && event.clientX > event.currentTarget.getBoundingClientRect().right) event.currentTarget.close();
});
window.matchMedia('(min-width: 1101px)').addEventListener('change', event => {
  if (event.matches && $('#docs-menu').open) {
    $('#docs-menu').close();
    $('#guide-title')?.focus({preventScroll: true});
  }
});
$('#docs-search').addEventListener('input', drawDocsTopics);
