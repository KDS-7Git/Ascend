"use strict";
const $ = (selector, root = document) => root.querySelector(selector);
const state = {token: sessionStorage.getItem("ascend-token"), minutes: null, overview: null, levels: [], tab: "today"};
let noticeTimer;
function el(tag, text, className) { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; }
function button(text, action, className = "secondary") { const node = el("button", text, className); node.type = "button"; node.addEventListener("click", () => Promise.resolve().then(action).catch(error => notify(error.message))); return node; }
function notify(message) { const node = $("#notice"); node.textContent = message; node.hidden = false; clearTimeout(noticeTimer); noticeTimer = setTimeout(() => node.hidden = true, 4500); }
async function api(path, body, method = "POST") {
  const headers = {}; if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const options = {headers, cache: "no-store"};
  if (body !== undefined) { options.method = method; if (body instanceof FormData) options.body = body; else { headers["Content-Type"] = "application/json"; options.body = JSON.stringify(body); } }
  let response;
  try { response = await fetch(`/api/${path}`, options); } catch { throw new Error("You're offline. Reconnect to save your progress."); }
  if (response.status === 401) { if (!$("#login-dialog").open) $("#login-dialog").showModal(); throw new Error("Sign in to continue."); }
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Please check the form fields.");
  return data;
}
const command = argv => api("command", {argv});
async function switchTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".screen").forEach(screen => screen.hidden = screen.id !== tab);
  document.querySelectorAll("[data-tab]").forEach(node => { node.classList.toggle("active", node.dataset.tab === tab); if (node.dataset.tab === tab) node.setAttribute("aria-current", "page"); else node.removeAttribute("aria-current"); });
  location.hash = tab;
  if (tab === "path") await renderPath();
  if (tab === "stats") await renderStats();
  if (tab === "more") await renderMore();
}
const ICONS = {
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
function challengeArt() {
  const art = svgElement('svg', {viewBox: '0 0 240 150', class: 'challenge-art', 'aria-hidden': 'true'});
  art.append(svgElement('path', {d:'M10 120C65 150 45 65 106 94S150 25 215 34', fill:'none', stroke:'currentColor', 'stroke-width':2, 'stroke-dasharray':'5 7'}));
  for (const [cx,cy,r] of [[10,120,5],[70,98,9],[130,94,6],[173,48,10],[215,34,17]]) {
    art.append(svgElement('circle',{cx,cy,r,fill:'var(--hero-bg)',stroke:'currentColor','stroke-width':2}));
  }
  art.append(svgElement('path',{d:'m208 34 5 5 9-10',fill:'none',stroke:'currentColor','stroke-width':3,'stroke-linecap':'round','stroke-linejoin':'round'}));
  return art;
}
let refreshVersion = 0;
async function refresh() {
  const version = ++refreshVersion;
  const [overview, levels] = await Promise.all([api('me' + (state.minutes ? `?minutes=${state.minutes}` : '')), api('levels')]);
  if (version !== refreshVersion) return;
  if (state.overview?.mission?.id !== overview.mission?.id) $('#session-result').hidden = true;
  state.overview = overview; state.levels = levels;
  $('#streak').textContent = overview.current_streak;
  $('#streak-link').setAttribute('aria-label', `View streak stats: ${overview.current_streak} days`);
  renderMissionProgress();
  const cards = $('#today-cards'); cards.replaceChildren();
  if (overview.next) cards.append(nodeCard(overview.next, false));
  else {
    const main = levels.filter(lv => lv.lane === 'main').flatMap(lv => lv.nodes), p = progressOf(main);
    const finished = main.length && p.resolved === p.total;
    const empty = el('div', undefined, 'card empty'); empty.append(icon(finished ? 'flag' : 'mountain'));
    empty.append(el('h2', !overview.mission ? 'Find your first summit.' : finished ? (p.skipped ? 'Your main path is explored.' : 'Your main path is complete!') : 'A smaller step, perhaps.'), el('p', !overview.mission ? 'Choose a track, then turn one small challenge into a real skill.' : finished ? 'Revisit a challenge, try an optional drill, or choose your next mission.' : 'No open challenge fits this time. Choose more time, or split a challenge into smaller steps from its details.'));
    empty.append(button(overview.mission ? 'Explore your path' : 'Choose a track', () => switchTab(overview.mission ? 'path' : 'more'), ''));
    cards.append(empty);
  }
  const aside = el('aside', undefined, 'today-aside');
  if (overview.quick_win) aside.append(nodeCard(overview.quick_win, true));
  const lv = currentLevel(), milestone = lv?.nodes.find(n => n.milestone && n.status === 'todo');
  if (milestone && milestone.id !== overview.next?.id) {
    const target = el('section', undefined, 'card summit-card');
    const label = el('p', undefined, 'eyebrow'); label.append(icon('flag'), document.createTextNode('YOUR NEXT MILESTONE'));
    target.append(label, el('h2', milestone.title.replace(/\s*\(milestone\)$/i, '')), el('p', 'Put this level’s skills together in one challenge.', 'muted'));
    target.append(progressBar(lv.nodes, `${lv.title} progress`), el('p', progressLabel(progressOf(lv.nodes)), 'small muted'), button('Preview milestone', () => showNode(milestone, lv), 'text-button'));
    aside.append(target);
  }
  if (aside.childElementCount) cards.append(aside);
  await refreshSessions();
}
function renderMissionProgress() {
  const root = $('#mission-progress'); root.replaceChildren();
  if (!state.overview.mission) return;
  const levels = state.levels.filter(lv => lv.lane === 'main'), current = currentLevel();
  const nodes = levels.flatMap(lv => lv.nodes), p = progressOf(nodes);
  const banner = el('section', undefined, 'mission-banner');
  const emblem = el('div', undefined, 'mission-emblem'); emblem.append(icon('route'));
  const info = el('div', undefined, 'mission-info'); info.append(el('p', 'YOUR ACTIVE TRACK', 'eyebrow'), el('h2', state.overview.mission.title), el('p', current ? `Level ${levels.indexOf(current) + 1} of ${levels.length} · ${current.title}` : 'Your mission is ready', 'muted small'));
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
function nodeCard(node, quick) {
  const card = el('article', undefined, `card node-card ${quick ? 'quick-card' : 'next-card'}${node.milestone ? ' milestone-hero' : ''}`);
  const label = el('p', undefined, 'eyebrow'); label.append(icon(quick ? 'bolt' : node.milestone ? 'flag' : 'play'), document.createTextNode(quick ? 'A LITTLE SIDE QUEST' : node.milestone ? 'MILESTONE CHALLENGE' : 'YOUR NEXT CHALLENGE'));
  card.append(label);
  const lv = levelFor(node);
  card.append(el('p', `${lv?.title || state.overview.mission?.title || ''}${state.overview.draft ? ' · Draft track' : ''}`, 'card-context'));
  card.append(el('h2', node.title), el('p', node.brief || node.done_when, 'description'));
  const meta = el('div', undefined, 'challenge-meta'); meta.append(el('span', `~${node.estimate} min`, 'pill'));
  if (node.steps?.length) meta.append(el('span', `${node.steps.length} steps to try`, 'small'));
  if (quick) meta.append(el('span', 'Optional', 'small'));
  card.append(meta);
  if (!quick && state.overview.resume) { const resume = el('p', undefined, 'resume-note'); resume.append(el('strong', 'Where you left off: '), document.createTextNode(state.overview.resume)); card.append(resume); }
  const actions = el('div', undefined, 'card-actions');
  const open = button(quick ? 'Try this challenge' : 'Open challenge', () => showNode(fullNode(node), lv), quick ? 'secondary' : ''); open.append(icon('arrow'));
  actions.append(open, button('Log progress', () => openLog(node), 'text-button')); card.append(actions);
  if (!quick) card.append(challengeArt());
  return card;
}
function openSheet() { const dialog = $('#sheet'); $('#sheet-content').replaceChildren(); if (!dialog.open) dialog.showModal(); return $('#sheet-content'); }
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
function openLog(node) {
  const content = openSheet(); const title = el('h2', 'Make your progress count.'); title.id = 'sheet-title';
  content.append(el('p', 'SAVE YOUR SESSION', 'eyebrow'), title, el('p', node.title, 'muted'));
  const form = el('form');
  const learned = field(form, 'learned', 'What I did', 'textarea'); learned.required = true; learned.minLength = 20; learned.placeholder = 'What did you try, discover, or build?';
  const next = field(form, 'next-step', "What's next", 'text', state.overview.resume || `Continue with ${node.title}`); next.required = true;
  const checkLabel = el('label', undefined, 'check completion-choice'); const complete = el('input'); complete.type = 'checkbox'; complete.id = 'complete';
  checkLabel.append(complete, document.createTextNode('Mark as done')); form.append(checkLabel);
  form.append(el('p', 'Leave unchecked to save a work-in-progress session.', 'small muted'));
  const details = el('details'); details.append(el('summary', 'Add details'));
  const minutes = field(details, 'minutes', 'Minutes spent', 'number'); minutes.min = '1'; minutes.max = '1440';
  const proof = field(details, 'proof', 'Proof link or file path');
  if (node.verify?.type && node.verify.type !== 'manual') form.append(el('p', 'Completion checks your evidence. If the check fails, your session is still saved.', 'small muted'));
  form.append(details);
  const error = el('p', '', 'error'); error.setAttribute('role', 'alert'); error.hidden = true;
  const submit = el('button', 'Save progress'); form.append(error, submit); content.append(form);
  complete.addEventListener('change', () => submit.textContent = complete.checked ? 'Complete challenge' : 'Save progress');
  form.addEventListener('submit', async event => {
    event.preventDefault(); submit.disabled = true;
    const previousLevels = state.levels;
    let saved = false;
    try {
      const result = await api('entries', {learned: learned.value, next_step: next.value, proof: proof.value || null, minutes: minutes.value ? Number(minutes.value) : null, node_id: `${node.pack_id}:${node.id}`, complete: complete.checked});
      saved = true; $('#sheet').close();
      await refresh(); if (state.tab === 'path') await renderPath();
      showSessionResult(node, result, previousLevels);
      notify(result.completed ? '✓ Challenge complete. Your path has moved forward.' : result.verification ? `Session saved. ${result.verification}` : '✓ Your progress is saved.');
    } catch (err) {
      if (saved) notify('Your session was saved, but the view could not refresh. Reload to see your progress.');
      else { error.textContent = err.message; error.hidden = false; }
    } finally { submit.disabled = false; }
  });
  learned.focus();
}
function showNode(node, level = levelFor(node)) {
  const content = openSheet(), status = node.status || 'todo';
  content.append(el('p', `${node.milestone ? 'MILESTONE' : 'CHALLENGE'} · ~${node.estimate} MIN`, 'eyebrow'));
  const title = el('h2', node.title); title.id = 'sheet-title'; content.append(title);
  if (node.brief) content.append(el('p', node.brief, 'challenge-brief'));
  const outcome = el('section', undefined, 'outcome'); outcome.append(el('h3', 'Your finish line'), el('p', node.done_when)); content.append(outcome); content.append(el('p', verificationLabel(node), 'verification-label'));
  if (node.steps?.length) {
    const list = el('ol', undefined, 'challenge-steps');
    for (const step of node.steps) list.append(el('li', step));
    content.append(el('h3', 'Try it step by step'), list);
  }
  const link = el('a', 'Open learning resource ↗', 'resource-link'); link.href = node.resource; link.target = '_blank'; link.rel = 'noopener noreferrer'; content.append(link);
  if (node.hints?.length) {
    const hints = el('section', undefined, 'challenge-hints'); hints.append(el('h3', 'A nudge if you need one'));
    node.hints.forEach((hint, i) => { const details = el('details'); details.append(el('summary', `Hint ${i + 1}`), el('p', hint)); hints.append(details); }); content.append(hints);
  }
  const locked = !node.open && status === 'todo';
  if (locked) {
    const all = state.levels.flatMap(lv => lv.nodes), missing = (node.needs || []).map(id => all.find(n => n.id === id)).filter(n => n && n.status === 'todo');
    content.append(el('p', missing.length ? `First complete: ${missing.map(n => n.title).join(', ')}.` : 'This challenge opens after the previous level’s milestone.', 'lock-note'));
  }
  const actions = el('div', undefined, 'dialog-actions');
  if (!locked) {
    const target = field(content, 'task-target-minutes', 'Session target (minutes)', 'input'); target.type = 'number'; target.min = 1; target.max = 1440; target.value = node.estimate;
    content.append(el('p', node.verify?.type === 'lab' || node.verify?.type === 'ctf' ? 'Verified completion earns up to 100 XP within the target; late rewards taper to 25 XP. Paused time is excluded. One reward per task.' : 'The timer records your session. Artifact and self-reviewed tasks do not earn automatic skill XP.', 'muted'));
    actions.append(button(node.verify?.type === 'lab' ? 'Start verified exercise' : 'Start timed task', async () => { await command(['session', 'start', `${node.pack_id}:${node.id}`, '--minutes', String(Number(target.value))]); await refreshSessions(); if (node.verify?.type === 'lab') await showLab(node); else notify('Task timer started.'); }, ''));
    if (node.verify?.type === 'ctf') actions.append(button('Verify lab completion', async () => { const result = await command(['check', `${node.pack_id}:${node.id}`, '--complete']); notify(result.summary); await refresh(); await refreshSessions(); if (state.tab === 'path') await renderPath(); }));
    actions.append(button(status === 'todo' ? 'Log progress' : 'Log another practice', () => openLog(node)));
  }
  if (status !== 'todo') content.append(el('p', status === 'done' ? '✓ Completed. Revisit this whenever you want to practice.' : 'Skipped. You can return to this challenge at any time.', 'muted'));
  content.append(actions);
  const manage = el('details', undefined, 'manage-challenge'); manage.append(el('summary', 'Challenge options'));
  if (node.verify?.type && node.verify.type !== 'manual') manage.append(button('Check evidence', async () => { const result = await command(['check', `${node.pack_id}:${node.id}`]); notify(result.summary); }));
  if (status === 'todo') {
    manage.append(button('Skip challenge', async () => { await api(`nodes/${node.pack_id}:${node.id}/mark`, {status: 'skipped'}); $('#sheet').close(); await refresh(); if (state.tab === 'path') await renderPath(); notify('Challenge skipped. You can return to it from your path.'); }));
    if (level && !level.open) manage.append(button('Unlock level early', async () => { await command(['unlock', level.id]); $('#sheet').close(); await refresh(); if (state.tab === 'path') await renderPath(); }));
    if (!['lab', 'ctf'].includes(node.verify?.type)) {
      const parts = field(manage, 'split-parts', 'Split into smaller steps (one per line)', 'textarea');
      manage.append(button('Save smaller steps', async () => { await command(['split', `${node.pack_id}:${node.id}`, ...parts.value.split('\n').filter(Boolean)]); $('#sheet').close(); await refresh(); if (state.tab === 'path') await renderPath(); }));
    }
  } else manage.append(button('Reopen challenge', async () => { await api(`nodes/${node.pack_id}:${node.id}/mark`, {status:'todo'}); $('#sheet').close(); await refresh(); if (state.tab === 'path') await renderPath(); }));
  content.append(manage);
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
}

async function renderStats() {
  const [stats, days, levels] = await Promise.all([api("stats"), api("heatmap"), api("levels")]); const root = $("#stats-content"); root.replaceChildren();
  const streak = el("section", undefined, "card"); streak.append(el("h2", "Showing up, one day at a time."), el("span", `${stats.current_streak}`, "streak-number"), el("span", ` days · best ${stats.best_streak}`, "muted"), el("p", `${stats.freeze_available} freeze available this week`, "muted"));
  const calendar = el("section", undefined, "card"); calendar.append(el("h2", "Your last 12 weeks")); const heat = el("div", undefined, "heatmap");
  for (const day of days) { const cell = el("div", undefined, `heat-day${day.count ? " logged" : ""}`); cell.title = `${day.day}: ${day.count} entries`; cell.setAttribute("aria-label", cell.title); cell.setAttribute("role", "img"); heat.append(cell); }
  calendar.append(heat);
  const minutes = el("section", undefined, "card"); minutes.append(el("h2", "Time well spent"), el("p", `${stats.minutes_this_week} minutes this week`, "muted")); const chart = el("div", undefined, "weekly-chart");
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
  minutes.append(chart); root.append(streak, calendar, minutes);
  const achievements = el("section", undefined, "card");
  achievements.append(el("h2", "Milestones you've earned"));
  const earned = levels.flatMap(level => level.nodes).filter(node => node.milestone && node.status === "done");
  const shelf = el("div", undefined, "earned-milestones");
  for (const node of earned) { const badge = el("div", undefined, "earned-badge"); badge.append(icon("flag"), el("span", node.title.replace(/\s*\(milestone\)$/i, ""))); shelf.append(badge); }
  if (!earned.length) achievements.append(el("p", "Complete a milestone in your active track to add it here. Each one represents a skill you've put into practice.", "muted"));
  else achievements.append(shelf);
  root.append(achievements);
  const session = await command(["session", "status"]);
  const xp = el("section", undefined, "card"); xp.append(el("h2", `${session.xp} verified XP`), el("p", `${session.verified_awards} graded or externally confirmed tasks. Artifact presence and manual marks do not earn these rewards.`)); root.append(xp);
}
async function renderMore() {
  const [packs, parked, account] = await Promise.all([api("packs"), command(["parked"]), api("account")]);
  $("#mission-name").textContent = state.overview?.mission?.title || "No active mission";
  $("#mission-time").value = state.overview?.mission?.nudge_time || "";
  $("#mission-pack").replaceChildren(...packs.map(pack => { const option = el("option", pack.id); option.value = pack.id; return option; }));
  $("#pack-list").replaceChildren();
  for (const pack of packs) { const row = el("div", undefined, "pack-item"); row.append(el("p", `${pack.id} · ${pack.reviewed ? "reviewed" : "draft / unreviewed"} · ${pack.trusted ? "commands trusted" : "commands untrusted"}`)); row.append(button("Read pack", async () => { const data = await api(`packs/${pack.id}`); const content = openSheet(); const heading = el("h2", data.title); heading.id = "sheet-title"; content.append(heading); for (const node of data.nodes) content.append(el("h3", node.title), el("p", node.done_when)); content.append(button("Mark reviewed", async () => { await command(["pack", "review", pack.id]); $("#sheet").close(); await renderMore(); })); })); $("#pack-list").append(row); }
  $("#parked-list").replaceChildren(...parked.map(idea => { const item = el("li", idea.note); item.append(button("Resolve", async () => { await command(["resolve", String(idea.id)]); await renderMore(); })); return item; }));
  $("#account-info").textContent = `${account.username} · ${location.origin}`;
  $("#account-timezone").value = account.timezone;
  $("#nudge-time").value = account.settings.nudge_time || "21:30";
  $("#nudge-channel").value = account.settings.nudge_channel || "ntfy";
  $("#ntfy-topic").value = account.settings.ntfy_topic || "";
  $("#nudge-enabled").checked = account.settings.nudge_enabled || false;
  $("#logout").hidden = account.auth_mode === "single";
  $("#public-streak").checked = account.settings.public_streak || false;
  $("#public-link").textContent = account.settings.public_streak ? `${location.origin}/api/public/${encodeURIComponent(account.username)}/badge.svg` : "Your streak is private.";
}
document.querySelectorAll("[data-icon]").forEach(node => node.append(icon(node.dataset.icon)));
window.addEventListener("hashchange", () => { const tab = location.hash.slice(1); if (["today", "path", "stats", "more"].includes(tab) && tab !== state.tab) switchTab(tab).catch(error => notify(error.message)); });
$("#jump-current").addEventListener("click", () => jumpToLevel(currentLevel()?.id));
document.querySelectorAll("[data-tab]").forEach(node => node.addEventListener("click", () => switchTab(node.dataset.tab).catch(error => notify(error.message))));
$("#streak-link").addEventListener("click", () => switchTab("stats").catch(error => notify(error.message)));
document.querySelectorAll("[data-minutes]").forEach(node => node.addEventListener("click", async () => { state.minutes = node.dataset.minutes || null; document.querySelectorAll("[data-minutes]").forEach(chip => chip.setAttribute("aria-pressed", String(chip === node))); try { await refresh(); } catch (error) { notify(error.message); } }));
$("#sheet .close").addEventListener("click", () => $("#sheet").close());
$("#sheet").addEventListener("click", event => { if (event.target === $("#sheet")) { const box = event.target.getBoundingClientRect(); if (event.clientY < box.top || event.clientX < box.left || event.clientX > box.right) event.target.close(); } });
function handleForm(selector, handler) { $(selector).addEventListener("submit", async event => { event.preventDefault(); try { await handler(event); } catch (error) { notify(error.message); } }); }
handleForm("#search-form", async () => { const results = await api(`search?q=${encodeURIComponent($("#search").value)}`); $("#search-results").replaceChildren(...results.map(entry => { const item = el("article", undefined, "search-result"); item.append(el("p", entry.learned), el("p", `${entry.day} · ${entry.node_id || "Personal note"}`, "muted")); return item; })); if (!results.length) $("#search-results").append(el("p", "No matching notes yet.", "muted")); });
handleForm("#install-form", async () => { await command(["pack", "install", $("#pack-id").value]); await renderMore(); notify("Pack installed. Read it before trusting its checks."); });
$("#pack-upload").addEventListener("change", async event => { if (!event.target.files[0]) return; const data = new FormData(); data.append("file", event.target.files[0]); try { await api("packs", data); await renderMore(); notify("Pack installed."); } catch (error) { notify(error.message); } });
$("#start-mission").addEventListener("click", async () => { try { const args = ["mission", "start", $("#mission-pack").value]; if ($("#mission-time").value) args.push("--nudge-time", $("#mission-time").value); await command(args); await refresh(); await renderMore(); notify("Mission started."); } catch (error) { notify(error.message); } });
for (const action of ["pause", "finish"]) $(`#${action}-mission`).addEventListener("click", async () => { try { await command(["mission", action]); await refresh(); await renderMore(); } catch (error) { notify(error.message); } });
$("#save-mission-time").addEventListener("click", async () => { try { await command(["mission", "nudge-time", $("#mission-time").value || "off"]); await refresh(); notify("Mission reminder saved."); } catch (error) { notify(error.message); } });
handleForm("#reminder-form", async () => { await command(["config", "nudge-time", $("#nudge-time").value]); await command(["config", "nudge-channel", $("#nudge-channel").value]); if ($("#ntfy-topic").value) await command(["config", "ntfy-topic", $("#ntfy-topic").value]); await command(["config", "nudge-enabled", String($("#nudge-enabled").checked)]); notify("Reminders saved."); });
$("#test-nudge").addEventListener("click", async () => { try { const result = await command(["config", "nudge-test"]); notify(result.sent ? "Test reminder sent." : result.reason); } catch (error) { notify(error.message); } });
handleForm("#park-form", async () => { await command(["park", $("#park-note").value]); $("#park-note").value = ""; await renderMore(); });
$("#save-timezone").addEventListener("click", async () => { try { await command(["config", "timezone", $("#account-timezone").value]); await refresh(); notify("Timezone saved."); } catch (error) { notify(error.message); } });
function setTheme(theme) { if (theme === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = theme; localStorage.setItem("ascend-theme", theme); }
$("#theme").value = localStorage.getItem("ascend-theme") || "system"; setTheme($("#theme").value);
$("#theme").addEventListener("change", event => setTheme(event.target.value));
$("#logout").addEventListener("click", async () => { try { await api("logout", {}); sessionStorage.removeItem("ascend-token"); state.token = null; location.reload(); } catch (error) { notify(error.message); } });
$("#public-streak").addEventListener("change", async event => { try { await command(["config", "public-streak", String(event.target.checked)]); await renderMore(); } catch (error) { notify(error.message); } });
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
refresh().then(() => switchTab(["today", "path", "stats", "more"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "today")).catch(error => notify(error.message));

// Timers are scored by the server; this display is only a synchronized preview.
async function refreshSessions() {
  state.sessions = await command(['session', 'status']);
  state.sessionFetched = performance.now();
  renderSessionClock();
}
function renderSessionClock() {
  const root = $('#task-session'); if (!root || !state.sessions) return;
  const current = state.sessions.active;
  const renderKey = current ? `active-${current.id}` : `paused-${state.sessions.paused.map(r => r.id).join('-')}`;
  const changed = root.dataset.session !== renderKey;
  if (changed) { root.replaceChildren(); root.dataset.session = renderKey; }
  root.hidden = !current && !state.sessions.paused.length;
  if (current) {
    const elapsed = current.elapsed_seconds + Math.floor((performance.now() - state.sessionFetched) / 1000);
    const remaining = Math.max(0, current.budget_seconds - elapsed);
    const clock = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}`;
    if (changed) {
      root.append(el('strong', current.title), el('span', '', 'session-clock'));
      root.append(button('Pause session', async () => { await command(['session', 'pause']); await refreshSessions(); }));
    }
    root.querySelector('.session-clock').textContent = remaining ? `${clock} remaining` : 'Target elapsed — keep going at your pace';
    const checkpoint = elapsed >= current.budget_seconds ? 2 : elapsed >= current.budget_seconds * .75 ? 1 : 0;
    const key = `ascend-session-notice-${current.id}`;
    if (checkpoint > Number(sessionStorage.getItem(key) || 0)) {
      sessionStorage.setItem(key, String(checkpoint));
      notify(checkpoint === 2 ? 'Your target time has elapsed. Verified completion still earns XP.' : 'Three quarters of your planned session has elapsed.');
    }
  } else if (changed && state.sessions.paused.length) {
    const saved = state.sessions.paused[state.sessions.paused.length - 1];
    root.append(el('strong', `Paused: ${saved.title}`), button('Resume session', async () => { await command(['session', 'start', `${saved.pack_id}:${saved.node_id}`]); await refreshSessions(); }));
  }
}
function verificationLabel(node) {
  return node.verify?.type === 'lab' ? (node.verify.exercise === 'case' ? 'Server-graded reasoning check' : 'Server-verified exercise') : node.verify?.type === 'ctf' ? 'Signed external lab evidence' : node.verify?.type === 'file' ? 'Artifact check · reasoning needs review' : 'Evidence review required';
}
async function showLab(node, fresh = false) {
  const ref = `${node.pack_id}:${node.id}`;
  const run = await command(['lab', 'start', ref, ...(fresh ? ['--fresh'] : [])]);
  const content = openSheet(), heading = el('h2', node.title); heading.id = 'sheet-title';
  content.append(el('p', verificationLabel(node), 'eyebrow'), heading, el('p', run.instructions, 'challenge-brief'));
  if (run.marker) content.append(el('p', `Your exercise marker: ${run.marker}`));
  if (run.exercise === 'logging' && !run.passed) {
    const actions = el('div', undefined, 'input-row');
    for (const kind of ['ok', 'error']) actions.append(button(kind === 'ok' ? 'Send successful request' : 'Send failed request', async () => { await command(['lab', 'emit', run.id, kind]); await showLab(node); }));
    content.append(actions);
  }
  if (Object.keys(run.data || {}).length) {
    content.append(el('h3', 'Exercise data'), el('pre', JSON.stringify(run.data, null, 2), 'lab-data'));
  }
  if (run.passed) content.append(el('p', '✓ This instance has passed. Repeating it does not award XP again.', 'success-note'));
  const form = el('form'); const inputs = {};
  for (const [key, value] of Object.entries(run.answer_template)) {
    const label = el('label', key.replaceAll('_', ' ')); label.htmlFor = `lab-answer-${key}`;
    let input;
    if (run.choices && key === 'choice') {
      const group = el('fieldset'); group.append(el('legend', 'Choose your decision'));
      for (const [id, text] of Object.entries(run.choices)) {
        const option = el('input'); option.type = 'radio'; option.name = 'case-choice'; option.value = id; option.required = true; option.disabled = run.passed;
        const card = el('label', undefined, 'case-choice'); card.append(option, el('span', `${id}: ${text}`)); group.append(card);
      }
      inputs[key] = {type: 'choice', input: group}; form.append(group); continue;
    } else { input = el('input'); input.type = typeof value === 'boolean' ? 'checkbox' : typeof value === 'number' ? 'number' : 'text'; }
    input.id = `lab-answer-${key}`; input.required = typeof value !== 'boolean'; input.disabled = run.passed;
    inputs[key] = {input, type: typeof value}; form.append(label, input);
  }
  const result = el('p'); result.setAttribute('role', 'status');
  const submit = el('button', 'Verify my result'); submit.type = 'submit'; submit.disabled = run.passed;
  form.append(submit, result); content.append(form);
  form.addEventListener('submit', async event => {
    event.preventDefault(); submit.disabled = true;
    try {
      const answers = Object.fromEntries(Object.entries(inputs).map(([key, entry]) => [key, entry.type === 'choice' ? entry.input.querySelector(':checked').value : entry.type === 'boolean' ? entry.input.checked : entry.type === 'number' ? Number(entry.input.value) : entry.input.value.trim()]));
      const checked = await command(['lab', 'submit', run.id, JSON.stringify(answers)]);
      result.textContent = checked.summary;
      if (checked.completed) {
        const gained = (checked.timer?.xp || 0) - (run.timer?.xp || 0);
        result.textContent = `✓ Verified.${gained > 0 ? ` +${gained} XP.` : ''} ${run.exercise === 'case' ? 'Your scenario decision passed; the hands-on assessment remains separate.' : 'The server recorded the demonstrated result.'}`;
        await refresh(); await refreshSessions(); if (state.tab === 'path') await renderPath();
      } else submit.disabled = false;
    } catch (error) { result.textContent = error.message; submit.disabled = false; }
  });
  content.append(button('Start a fresh exercise instance', () => showLab(node, true)));
  await refreshSessions();
}
async function browseTracks() {
  const [catalog, installed] = await Promise.all([command(['pack', 'registry']), api('packs')]);
  const installedIds = new Set(installed.map(p => p.id));
  const content = openSheet(), title = el('h2', 'Find a track'); title.id = 'sheet-title'; content.append(title);
  const search = field(content, 'catalog-search', 'Search subjects and roles', 'input'); search.type = 'search'; search.placeholder = 'SOC, red team, cloud, Android…';
  const filter = el('select'); filter.setAttribute('aria-label', 'Track category');
  for (const group of ['All subjects', ...new Set(catalog.map(p => p.category || 'Projects'))]) { const option = el('option', group); option.value = group; filter.append(option); }
  const count = el('p', '', 'muted'), list = el('div', undefined, 'catalog-results'); content.append(filter, count, list);
  function draw() {
    const query = search.value.toLowerCase().trim();
    const matches = catalog.filter(p => (filter.value === 'All subjects' || (p.category || 'Projects') === filter.value) && [p.title, p.id, ...(p.aliases || [])].join(' ').toLowerCase().includes(query));
    count.textContent = `${matches.length} tracks · all supplied curricula remain drafts`; list.replaceChildren();
    for (const pack of matches) {
      const card = el('article', undefined, 'catalog-card'); card.append(el('p', pack.category || 'Project', 'eyebrow'), el('h3', pack.title));
      if (pack.entry) card.append(el('p', `Entry skills: ${pack.entry}`));
      if (pack.limits) { const details = el('details'); details.append(el('summary', 'Environment and assessment limits'), el('p', pack.limits)); card.append(details); }
      if (pack.main_levels) card.append(el('p', `${pack.main_levels} levels · ${pack.nodes} tasks`, 'muted'));
      const install = button(installedIds.has(pack.id) ? 'Installed' : 'Install track', async () => { await command(['pack', 'install', pack.id]); installedIds.add(pack.id); await renderMore(); draw(); notify('Track installed. Your active mission is unchanged.'); }); install.disabled = installedIds.has(pack.id); card.append(install); list.append(card);
    }
  }
  search.addEventListener('input', draw); filter.addEventListener('change', draw); draw(); search.focus();
}
$('#browse-tracks').addEventListener('click', browseTracks);
setInterval(renderSessionClock, 1000);
setInterval(() => { if (state.overview && !document.hidden && !$('#login-dialog').open) refreshSessions().catch(() => {}); }, 30000);
