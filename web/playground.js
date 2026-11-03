"use strict";

let playgroundDraft = null;
let playgroundSaveTimer;
let playgroundRenderVersion = 0;
let playgroundFieldId = 0;
let playgroundClock = null;
const playgroundFilters = {};
const playgroundLabel = a => a.role === 'example' ? 'Worked example' : a.kind === 'free' ? 'Free practice' : `${a.difficulty[0].toUpperCase() + a.difficulty.slice(1)} challenge`;
const playgroundOpen = route => switchTab(['quick', 'challenges', 'free', 'labs', 'history'].includes(route) ? 'playground' : 'activity', {topic: route});
const playgroundAction = (id, action, body = {}) => api(`playground/runs/${id}/${action}`, body);

async function savePlaygroundDraft(pause = false) {
  clearTimeout(playgroundSaveTimer);
  const draft = playgroundDraft;
  if (!draft) return;
  const work = draft.capture();
  if ((pause && draft.status === 'active') || JSON.stringify(work) !== draft.saved) {
    await playgroundAction(draft.id, 'save', {data: work, pause});
    draft.saved = JSON.stringify(work);
    try { sessionStorage.removeItem(draft.key); } catch { /* Server save is authoritative. */ }
  }
  if (pause) playgroundDraft = null;
}
function rememberPlayground(root, run, capture) {
  const key = `ascend-playground-${state.account?.username || 'local'}-${run.id}`;
  playgroundDraft = {id: run.id, status:run.status, key, capture, saved: run.local_draft_restored ? '' : JSON.stringify(capture())};
  root.addEventListener('input', () => {
    const status = $('#pg-save-status'); if (status) status.textContent = 'Saving your work…';
    try { sessionStorage.setItem(key, JSON.stringify({work: capture(), updated_at: run.updated_at})); } catch { /* Server save remains available. */ }
    clearTimeout(playgroundSaveTimer);
    playgroundSaveTimer = setTimeout(() => savePlaygroundDraft().then(() => { if (status) status.textContent = 'Saved in Playground → Saved work & history'; }).catch(error => { if (status) status.textContent = 'Not synced — draft kept in this tab'; notify(`Draft is kept in this tab. ${error.message}`, 'error'); }), 800);
  });
}
function playgroundLocalWork(run) {
  try {
    const saved = sessionStorage.getItem(`ascend-playground-${state.account?.username || 'local'}-${run.id}`);
    const local = saved ? JSON.parse(saved) : null;
    if (local?.updated_at === run.updated_at && ['active', 'saved'].includes(run.status)) {
      run.local_draft_restored = true;
      return {...run.work, ...local.work};
    }
    return run.work;
  } catch { return run.work; }
}
function playgroundField(root, label, value = '', type = 'text', options = null) {
  const wrap = el('div', undefined, 'pg-field'), caption = el('label', label);
  const input = el(options ? 'select' : type === 'textarea' ? 'textarea' : 'input');
  input.id = `pg-field-${++playgroundFieldId}`; caption.htmlFor = input.id; wrap.append(caption);
  if (options) {
    for (const option of options) {
      const [val, text] = Array.isArray(option) ? option : [option, option];
      const item = el('option', text); item.value = val; input.append(item);
    }
  } else if (type !== 'textarea') input.type = type;
  input.value = value ?? ''; wrap.append(input); root.append(wrap); return input;
}
function playgroundData(root, data) {
  if (Array.isArray(data)) {
    if (data.every(v => v && typeof v === 'object' && !Array.isArray(v))) {
      const wrap = el('div', undefined, 'pg-table-wrap'); wrap.tabIndex = 0; wrap.setAttribute('role', 'region'); wrap.setAttribute('aria-label', 'Evidence table');
      const table = el('table', undefined, 'pg-table');
      const keys = [...new Set(data.flatMap(Object.keys))];
      const head = el('thead'), tr = el('tr');
      keys.forEach(k => { const th = el('th', k.replaceAll('_', ' ')); th.scope = 'col'; tr.append(th); }); head.append(tr); table.append(head);
      const body = el('tbody');
      data.forEach(row => { const tr = el('tr'); keys.forEach(k => tr.append(el('td', typeof row[k] === 'object' ? JSON.stringify(row[k]) : String(row[k] ?? '')))); body.append(tr); });
      table.append(body); wrap.append(table); root.append(wrap);
    } else root.append(el('p', data.join(', ')));
  } else if (data && typeof data === 'object') {
    for (const [key, value] of Object.entries(data)) {
      const section = el('section', undefined, 'pg-evidence'); section.append(el('h3', key.replaceAll('_', ' ')));
      playgroundData(section, value); root.append(section);
    }
  } else root.append(el('pre', String(data), 'pg-text-evidence'));
}
function playgroundRecommendation(data, minutes, filters = {}, excluded = []) {
  const card = el('section', undefined, 'card pg-recommendation');
  const label = el('p', undefined, 'eyebrow'); label.append(icon('bolt'), document.createTextNode('OPTIONAL PRACTICE')); card.append(label);
  const item = data?.activities?.[0];
  if (item) {
    card.append(el('h2', item.title), el('p', `${playgroundLabel(item)} · ${item.minutes} min · no setup`, 'muted'));
    if (item.selection_minutes > item.minutes) card.append(el('p', `Allow ${item.selection_minutes} min at your reported pace (${item.timing_samples} completed sessions).`, 'small'));
    const actions = el('div', undefined, 'recommendation-actions');
    actions.append(button(item.role === 'example' ? 'Start guided example' : 'Start practice', () => startPlayground(item), ''));
    actions.append(button('Choose another', async () => {
      const skip = [...excluded, item.id], params = new URLSearchParams({...filters, minutes: minutes || 1440});
      params.set('exclude', skip.join(','));
      const result = await api(`playground/recommendations?${params}`);
      card.replaceWith(playgroundRecommendation(result, minutes, filters, skip));
    }, 'text-button')); card.append(actions);
  } else card.append(el('h2', 'Choose your practice'), el('p', data?.reason || 'A short worked example is a good place to begin.'));
  const link = el('a', 'Browse Playground', 'resource-link'); link.href = '#playground/quick'; card.append(link);
  return card;
}
async function startPlayground(item, deliberate = false, endScored = false) {
  await savePlaygroundDraft(true);
  const detail = await api(`playground/activities/${item.id}`);
  if (!detail.recommended_ready && !deliberate) {
    const root = openSheet('Preparation'); root.append(el('h2', item.title), el('p', 'Your background for this activity is not established yet. Its difficulty and finish line stay the same.'));
    root.querySelector('h2').id = 'sheet-title';
    for (const example of detail.preparation_options) root.append(button(`Study: ${example.title} · ${example.minutes} min`, async () => { $('#sheet').close(); await startPlayground(example); }));
    root.append(button('Choose an easier challenge', async () => { $('#sheet').close(); await playgroundOpen('quick'); }));
    root.append(button('Try this challenge', async () => { $('#sheet').close(); await startPlayground(item, true); }, ''));
    return;
  }
  const sessions = await command(['session', 'status']);
  const timed = sessions.active;
  if (timed && !endScored) {
    const root = openSheet('Switch activity'); root.append(el('h2', 'End scored attempt and switch'), el('p', `“${timed.title}” is still timed. Ending stops its clock without completion or XP. Its saved work and original attempt remain available.`));
    root.querySelector('h2').id = 'sheet-title';
    root.append(button('End scored attempt and switch', async () => { $('#sheet').close(); await startPlayground(item, deliberate, true); }, ''), button('Keep working on this attempt', () => $('#sheet').close()));
    return;
  }
  const run = await api(`playground/activities/${item.id}/start`, {deliberate, end_scored: endScored});
  await refreshSessions(); await playgroundOpen(run.id);
}
async function resumePlayground(run, endScored = false) {
  await savePlaygroundDraft(true);
  const sessions = await command(['session', 'status']);
  const timed = sessions.active;
  if (timed && !endScored) {
    const root = openSheet('Resume saved work'); root.append(el('h2', 'End scored attempt and switch'), el('p', `This ends “${timed.title}” and stops its clock without completion or XP. Your saved activity will resume with the same fixture.`));
    root.querySelector('h2').id = 'sheet-title';
    root.append(button('End scored attempt and switch', async () => { $('#sheet').close(); await resumePlayground(run, true); }, ''), button('Cancel', () => $('#sheet').close()));
    return;
  }
  await playgroundAction(run.id, 'resume', {end_scored: endScored});
  await refreshSessions(); await playgroundOpen(run.id);
}
function playgroundCard(item) {
  const card = el('article', undefined, 'card pg-catalog-card');
  card.dataset.role = item.role === 'example' ? 'lesson' : item.kind === 'free' ? 'workspace' : 'challenge';
  const emblem = el('div', undefined, 'pg-emblem'); emblem.append(icon(item.role === 'example' ? 'book' : item.kind === 'free' ? 'settings' : item.format === 'mystery' ? 'lock' : 'flag')); card.append(emblem);
  card.append(el('p', playgroundLabel(item), 'eyebrow'), el('h2', item.title));
  if (item.brief) card.append(el('p', item.brief));
  if (item.selection_minutes > item.minutes) card.append(el('p', `About ${item.selection_minutes} min at your reported pace`, 'small'));
  card.append(el('p', `${item.minutes} min · ${{cyber:'Cybersecurity', python:'Python', '3d':'3D fundamentals'}[item.domain || 'cyber']} · ${item.progress === 'solved' && item.role === 'example' ? 'studied' : item.progress}`, 'small muted'));
  if (item.role === 'example') card.append(el('p', '3 guided steps · try a prediction · reflect', 'pg-card-promise'));
  else if (item.kind === 'free') card.append(el('p', 'Change inputs. Compare results. Keep experimenting.', 'pg-card-promise'));
  else card.append(el('p', `${item.format === 'mystery' ? 'Investigate an unseen case' : 'Apply the skill on your own'} · ${item.award || (item.kind === 'quick' ? 10 : 0)} XP eligible`, 'pg-card-promise'));
  if (item.role !== 'example' && item.kind !== 'free') card.append(el('p', item.hint_policy === 'limited' ? 'Optional limited hints' : 'Independent challenge · no hints', 'small'));
  const background = el('details'); background.append(el('summary', 'Background and preparation'));
  background.append(el('p', `${item.setup} · phone or computer · ${item.verification}`, 'small'));
  item.prerequisites.forEach(ability => background.append(el('p', `${ability} · ${item.readiness[ability]}`, 'small')));
  background.append(el('p', `Separate preparation: up to ${item.preparation_minutes} min. The activity estimate above does not include optional study.`, 'small'));
  item.preparation_options.forEach(example => background.append(button(example.title, () => startPlayground(example), 'text-button')));
  if (item.role !== 'example') card.append(background);
  const actions = el('div', undefined, 'pg-actions'); actions.append(button(item.role === 'example' ? 'Study example' : item.kind === 'free' ? 'Open workspace' : 'Start challenge', () => startPlayground(item), ''));
  if (item.saved_runs.length) actions.append(button('Resume saved work', () => resumePlayground(item.saved_runs[0])));
  actions.append(button(item.bookmarked ? 'Remove bookmark' : 'Bookmark', async () => {
    await api(`playground/activities/${item.id}/bookmark?enabled=${!item.bookmarked}`, {}); await renderPlayground();
  }, 'text-button'));
  card.append(actions); return card;
}
async function renderPlayground() {
  if (state.tab === 'activity') return renderActivity();
  const version = ++playgroundRenderVersion;
  clearTimeout(playgroundSaveTimer); playgroundDraft = null;
  const route = state.playgroundRoute || 'quick';
  const root = $('#playground-content'); root.replaceChildren();
  document.querySelectorAll('.playground-tabs a').forEach(a => {
    if (a.hash === `#playground/${route}`) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  if (route === 'labs') return renderLabCatalog(root);
  if (!['quick', 'challenges', 'free', 'history'].includes(route)) {
    const run = await api(`playground/runs/${encodeURIComponent(route)}`);
    if (version === playgroundRenderVersion) renderPlaygroundRun(root, run);
    return;
  }
  if (route === 'history') {
    const history = await api('playground/history');
    if (version !== playgroundRenderVersion) return;
    renderHistoryLibrary(root, history);
    return;
  }
  const kind = {quick: 'quick', challenges: 'challenge', free: 'free'}[route];
  const filters = playgroundFilters[route] ||= {minutes: route === 'quick' ? '10' : '', domain: '', topic: '', difficulty: '', format: '', progress: '', environment: '', search: '', bookmarked: false};
  if (route === 'free') root.append(el('p', 'Change inputs and inspect the results. Save and resume whenever you like. Learning notes can count toward your streak; a workspace has no assessment XP.'));
  if (route === 'quick') {
    const recommendation = await api(`playground/recommendations?minutes=${filters.minutes || 15}${filters.topic ? `&topic=${filters.topic}` : ''}${filters.domain ? `&domain=${filters.domain}` : ''}`);
    if (version !== playgroundRenderVersion) return;
    root.append(playgroundRecommendation(recommendation, filters.minutes || 15, {topic: filters.topic, domain: filters.domain}));
    api('playground/selection', {data:{minutes:Number(filters.minutes || 15), kind:'quick', topic:filters.topic, domain:filters.domain}}).catch(() => {});
  }
  const form = el('form', undefined, 'pg-filters');
  playgroundField(form, 'Search', filters.search, 'search').addEventListener('input', e => filters.search = e.target.value);
  const controls = [
    ['domain', 'Subject', [['', 'All subjects'], ['cyber', 'Cybersecurity'], ['python', 'Python'], ['3d', '3D fundamentals']]],
    ['minutes', 'Time available', [['', 'Any duration'], ['5', '5 minutes'], ['10', '10 minutes'], ['15', '15 minutes'], ['30', '30 minutes'], ['60', '60 minutes'], ['120', 'Up to 2 hours']]],
    ['topic', 'Topic', [['', 'All topics'], ['access', 'Permissions'], ['subnet', 'Networking'], ['logging', 'Logging'], ['integrity', 'Integrity'], ['timeline', 'Timelines'], ['investigation', 'Investigations'], ['python', 'Python reasoning'], ['spatial', 'Coordinates & transforms']]],
    ['difficulty', 'Difficulty', [['', 'All difficulties'], ['easy', 'Easy'], ['intermediate', 'Intermediate'], ['hard', 'Hard']]],
    ['format', 'Format', [['', 'All formats'], ['exercise', 'Exercise / example'], ['transfer', 'Changed condition'], ['repair', 'Repair'], ['mystery', 'Mystery'], ['workspace', 'Workspace']]],
    ['environment', 'Setup', [['', 'Any setup'], ['browser', 'Browser only'], ['external', 'External setup']]],
    ['progress', 'Progress', [['', 'Any progress'], ['new', 'New'], ['started', 'Started'], ['solved', 'Solved']]],
  ];
  const advanced = el('details', undefined, 'pg-advanced'); advanced.append(el('summary', 'More filters'));
  const extra = el('div', undefined, 'pg-filters'); advanced.append(extra);
  controls.forEach(([key, label, options]) => playgroundField(['domain', 'minutes'].includes(key) ? form : extra, label, filters[key], 'text', options).addEventListener('change', e => filters[key] = e.target.value));
  const bookmark = el('label', undefined, 'check'), check = el('input'); check.type = 'checkbox'; check.checked = filters.bookmarked;
  check.addEventListener('change', () => filters.bookmarked = check.checked); bookmark.append(check, document.createTextNode('Bookmarked')); extra.append(bookmark);
  const apply = el('button', 'Apply filters'); form.append(apply);
  form.append(advanced);
  form.addEventListener('submit', e => { e.preventDefault(); runAction(apply, renderPlayground); }); root.append(form);
  root.append(button('Surprise me', async () => {
    const params = new URLSearchParams({kind, minutes: filters.minutes || (kind === 'quick' ? '15' : '120')});
    for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
    const data = await api(`playground/recommendations?${params}`);
    if (!data.activities.length) {
      notify(data.reason);
      const preparation = el('section', undefined, 'card pg-result'); preparation.append(el('h2', 'Start with preparation'));
      data.alternatives.forEach(item => preparation.append(button(`${item.title} · ${item.minutes} min`, () => startPlayground(item)))); root.prepend(preparation); return;
    }
    await startPlayground(data.activities[0]);
  }, 'secondary'));
  const params = new URLSearchParams({kind});
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
  const result = await api(`playground?${params}`);
  if (version !== playgroundRenderVersion) return;
  if (filters.format === 'mystery' && filters.topic) root.append(el('p', 'Topic context is visible in this selection. Previously seen cases are labeled familiar practice.', 'muted'));
  if (!result.activities.length) {
    root.append(el('p', result.empty_reason));
    result.alternatives.forEach(item => root.append(button(`${item.title} · ${item.minutes} min`, () => startPlayground(item))));
  }
  const groups = [
    ['Learn with guidance', 'New to a skill? Follow an explained example, make a prediction, then write what you learned.', a => a.role === 'example', 'lessons'],
    ['Test yourself', 'Solve a fresh problem independently. Evidence checks tell you when it is complete.', a => a.role !== 'example' && a.kind !== 'free', 'challenges'],
    ['Experiment freely', 'Editable workspaces with no required answer. Your changes stay here for next time.', a => a.kind === 'free', 'workspaces'],
  ];
  for (const [title, description, matches, kind] of groups) {
    const items = result.activities.filter(matches); if (!items.length) continue;
    const section = el('section', undefined, `pg-shelf pg-shelf-${kind}`);
    section.append(el('h2', title), el('p', description, 'muted'));
    const grid = el('div', undefined, 'pg-catalog'); items.forEach(item => grid.append(playgroundCard(item))); section.append(grid); root.append(section);
  }
}

async function renderActivity() {
  const version = ++playgroundRenderVersion;
  clearTimeout(playgroundSaveTimer); playgroundDraft = null;
  const root = $('#activity-content'); root.replaceChildren();
  const run = await api(`playground/runs/${encodeURIComponent(state.activityRef)}`);
  if (version !== playgroundRenderVersion || state.tab !== 'activity') return;
  $('.pg-back').href = `#playground/${run.kind === 'challenge' ? 'challenges' : run.kind === 'free' ? 'free' : 'quick'}`;
  renderPlaygroundRun(root, run);
  window.AscendContext?.render();
}

function renderPlaygroundTimer(root, run) {
  const bar = el('div', undefined, 'pg-session-bar');
  const clock = el('div', undefined, 'pg-clock'); clock.append(el('strong', '', 'pg-clock-value'), el('span', '', 'small muted'));
  bar.append(clock, el('p', 'Take your time. This clock does not affect XP.', 'small muted'));
  if (run.status === 'active') bar.append(button('Pause & save', async () => { await savePlaygroundDraft(true); await renderActivity(); }));
  else if (run.status === 'saved') bar.append(button('Resume activity', () => resumePlayground(run), ''));
  root.append(bar);
  playgroundClock = {id:run.id, timer:run.timer, at:performance.now(), node:clock};
  tickPlaygroundClock();
}
function tickPlaygroundClock() {
  if (!playgroundClock || state.tab !== 'activity' || !playgroundClock.node.isConnected) return;
  const {timer, at, node} = playgroundClock;
  const seconds = timer.elapsed_seconds + (timer.running ? Math.floor((performance.now() - at) / 1000) : 0);
  $('strong', node).textContent = formatTime(seconds);
  $('span', node).textContent = `${timer.running ? 'Time practicing' : 'Clock stopped'} · about ${Math.round(timer.target_seconds / 60)} min planned`;
}
setInterval(tickPlaygroundClock, 1000);

function renderPlaygroundTour(root, run, form) {
  const host = el('section', undefined, 'pg-tour'); host.setAttribute('aria-label', 'Guided walkthrough');
  const steps = el('ol', undefined, 'pg-learning-steps'); steps.setAttribute('aria-label', 'Learning sequence');
  for (const [i, label] of ['Walkthrough', 'Your takeaway', 'Fresh challenge'].entries()) {
    const step = el('li', label); step.dataset.step = i + 1; steps.append(step);
  }
  root.append(steps, host, form);
  const terminal = ['passed', 'ended'].includes(run.status);
  let current = run.tour.step || 0;
  let active = !terminal && ['pending', 'active'].includes(run.tour.status);
  const persist = async status => { await playgroundAction(run.id, 'tour', {step:current, status}); };
  const close = async status => {
    await persist(status); run.tour.status = status; active = false; draw();
    window.AscendMotion?.feedback?.(host, status === 'finished' ? 'complete' : 'info');
    const heading = form.querySelector('h2'); heading.tabIndex = -1;
    heading.focus({preventScroll: true}); host.scrollIntoView({block: 'start', behavior: 'instant'});
  };
  const draw = (focus = false) => {
    host.replaceChildren();
    host.classList.toggle('pg-tour-review', terminal && !active);
    form.hidden = active;
    [...steps.children].forEach((step, i) => {
      step.removeAttribute('aria-current');
      step.dataset.done = String(i === 0 && run.tour.status === 'finished' || i === 1 && run.status === 'passed');
      if (i === (active ? 0 : terminal ? 2 : 1)) step.setAttribute('aria-current', 'step');
    });
    if (!active) {
      const finished = run.tour.status === 'finished';
      const status = terminal ? el('div') : AscendFeedback.create({kind: finished ? 'success' : 'info', title: finished ? 'Walkthrough complete' : 'Ready to try it yourself?', message: 'Next: capture one takeaway in your own words.', compact: true});
      status.classList.add('pg-tour-finished');
      status.append(button(finished || terminal ? 'Redo walkthrough' : 'Open walkthrough', async () => {
        await playgroundAction(run.id, 'tour', {step: 0, status: 'active'});
        active = true; current = 0; draw(true);
      }, 'text-button'));
      host.append(status);
      return;
    }
    const lesson = run.teaching_steps[current];
    const progress = el('progress', undefined, 'pg-tour-progress'); progress.max = run.teaching_steps.length; progress.value = current + 1; progress.setAttribute('aria-label', 'Walkthrough progress');
    const top = el('div', undefined, 'pg-tour-top'); top.append(el('p', `STEP ${current + 1} OF ${run.teaching_steps.length}`, 'eyebrow'), button('Skip tour', () => close('skipped'), 'text-button'));
    const heading = el('h2', lesson.title); heading.tabIndex = -1;
    host.append(top, progress, heading, el('p', lesson.body));
    if (lesson.evidence) playgroundData(host, lesson.evidence);
    if (lesson.question) {
      const choices = el('fieldset', undefined, 'pg-prediction'); choices.append(el('legend', lesson.question));
      const explanation = el('div', undefined, 'pg-prediction-feedback'); explanation.setAttribute('role', 'status');
      lesson.choices.forEach((choice, index) => choices.append(button(choice, () => {
        choices.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.textContent === choice)));
        AscendFeedback.set(explanation, {kind: index === lesson.answer ? 'success' : 'warning', title: index === lesson.answer ? 'That’s right.' : 'Let’s work through it.', message: lesson.explanation, compact: true});
        window.AscendMotion?.feedback?.(explanation, index === lesson.answer ? 'success' : 'info');
      })));
      host.append(choices, explanation);
    }
    const actions = el('div', undefined, 'pg-actions');
    const back = button('Back', async () => { await playgroundAction(run.id, 'tour', {step:current - 1, status:'active'}); current--; draw(true); }); back.disabled = current === 0;
    actions.append(back, button(current === run.teaching_steps.length - 1 ? 'Finish walkthrough' : 'Next step', async () => {
      if (current === run.teaching_steps.length - 1) { await close('finished'); }
      else { await playgroundAction(run.id, 'tour', {step:current + 1, status:'active'}); current++; draw(true); }
    }, '')); host.append(actions);
    if (focus) { heading.focus({preventScroll: true}); host.scrollIntoView({block: 'start', behavior: 'instant'}); window.AscendMotion?.feedback?.(heading, 'step'); }
  };
  host.addEventListener('keydown', e => { if (e.key === 'Escape' && active) { e.preventDefault(); close('skipped').catch(error => notify(error.message, 'error')); } });
  draw();
}

function renderPlaygroundRun(root, run) {
  const terminal = ['passed', 'ended'].includes(run.status), work = playgroundLocalWork(run);
  root.dataset.role = run.role === 'example' ? 'lesson' : run.kind === 'free' ? 'workspace' : 'challenge';
  renderPlaygroundTimer(root, run);
  root.append(el('p', `${playgroundLabel(run.activity)} · ${run.activity.minutes} min · ${run.familiar ? 'Familiar practice' : run.activity.format === 'mystery' ? 'Unseen case' : 'Fresh exercise'} · ${run.status}`, 'eyebrow'));
  const title = el('h1', run.activity.title); title.id = 'activity-title'; title.tabIndex = -1; root.append(title);
  document.title = `${run.activity.title} · Ascend`;
  const mission = el('div', undefined, 'pg-mission'); mission.append(el('h2', run.role === 'example' ? 'What you’ll do' : run.kind === 'free' ? 'Your workspace' : 'Your objective'), el('p', run.role === 'example' ? 'Follow the steps, try the predictions, then explain one takeaway in your own words. Finish the example, then try a suggested fresh challenge.' : run.kind === 'free' ? 'Change inputs and run an experiment. Compare the output, then save anything you want to return to.' : 'Read the evidence and fill in the answer fields. Select Check evidence to test your explanation.')); root.append(mission);
  const storage = el('p', 'Answers and notes save automatically in your Ascend profile → Playground → Saved work & history.', 'small muted'); storage.id = 'pg-save-status'; storage.setAttribute('role', 'status'); root.append(storage);
  mission.hidden = terminal; storage.hidden = terminal;
  if (run.kind === 'free') return renderPlaygroundWorkspace(root, run, work);
  let reference;
  if (run.role === 'example') {
    reference = el('details', undefined, 'pg-reference'); reference.append(el('summary', 'Read the full worked example'), el('p', run.instructions));
    playgroundData(reference, run.activity.topic === 'integrity' ? Object.fromEntries(Object.entries(run.data).map(([k,v]) => [`${k} (escaped text)`, JSON.stringify(v)])) : run.data);
    reference.append(el('h3', 'Worked reasoning'), el('p', run.debrief));
  } else {
    root.append(el('p', run.instructions, 'challenge-brief'));
    const evidence = el('section', undefined, 'pg-case-evidence'); evidence.append(el('h2', 'Evidence')); playgroundData(evidence, run.data); root.append(evidence);
  }
  const form = el('form', undefined, 'pg-answer-form'), inputs = {};
  if (run.role === 'example') form.classList.add('pg-takeaway');
  form.append(el('h2', run.role === 'example' ? terminal ? 'Your takeaway' : 'Finish with a takeaway' : 'Your answer'));
  for (const [key, f] of Object.entries(run.fields)) {
    const options = f.type === 'boolean' ? [['', 'Choose an answer'], ['true', 'Yes'], ['false', 'No']] : f.options ? [['', 'Choose an answer'], ...f.options] : null;
    const input = playgroundField(form, f.label, work.answers?.[key] ?? '', f.type === 'integer' ? 'number' : 'text', options);
    input.required = true; input.disabled = terminal || run.status === 'saved'; if (f.type === 'integer') input.step = 1;
    inputs[key] = input;
  }
  const notes = playgroundField(form, run.role === 'example' ? 'In your own words: what did you learn?' : 'Notes and hypotheses (optional)', work.notes || '', 'textarea');
  if (run.role === 'example') {
    notes.id = 'pg-reflection'; notes.previousElementSibling.htmlFor = notes.id;
    const prompt = el('p', run.reflection_prompt, 'field-help'); prompt.id = 'pg-reflection-help'; notes.setAttribute('aria-describedby', prompt.id); notes.parentElement.append(prompt);
  }
  const reminder = el('details', undefined, 'pg-reminder'); reminder.append(el('summary', 'Leave a reminder for later (optional)'), el('p', 'This is a note to your future self, such as “compare the newline next time”. It is saved with this activity, not a new task or a required answer.', 'small muted'));
  const next = playgroundField(reminder, 'When I return, I want to…', work.next_step || '', 'text'); form.append(reminder);
  const capture = () => ({...work, notes: notes.value, next_step: next.value, answers: Object.fromEntries(Object.entries(inputs).map(([key, input]) => [key, run.fields[key].type === 'boolean' ? input.value === '' ? '' : input.value === 'true' : run.fields[key].type === 'integer' ? input.value === '' ? '' : Number(input.value) : input.value]))});
  rememberPlayground(form, run, capture);
  if (run.role === 'example') { notes.required = !terminal; notes.minLength = 20; }
  const actions = el('div', undefined, 'pg-actions');
  if (!terminal && run.status === 'active') {
    const submit = el('button', run.role === 'example' ? 'Finish example' : 'Check evidence'); actions.append(submit);
    form.addEventListener('submit', e => {
      e.preventDefault(); runAction(submit, async () => {
        await savePlaygroundDraft();
        const result = await playgroundAction(run.id, 'submit', {data: capture().answers, learned: notes.value, next_step: next.value});
        playgroundDraft = null;
        await refresh(); await renderPlayground();
        const feedback = $('#activity-content .pg-completion');
        if (feedback) {
          feedback.tabIndex = -1; feedback.focus({preventScroll: true}); feedback.scrollIntoView({block: 'start', behavior: 'instant'});
          window.AscendMotion?.feedback?.(feedback, result.result.passed ? 'complete' : 'info');
        } else notify(result.result.message, result.result.passed ? 'success' : 'error');
      });
    });
  }
  actions.append(button(terminal ? 'Back to saved work' : 'Save & leave', async () => { await savePlaygroundDraft(true); notify('Saved in Playground → Saved work & history. Resume from there whenever you’re ready.', 'success'); await playgroundOpen('history'); }));
  if (run.role !== 'example') actions.append(button('Save learning note', async () => {
    await savePlaygroundDraft(); await playgroundAction(run.id, 'log', {learned: notes.value, next_step: next.value}); notify('Learning note saved in your Ascend activity history.', 'success'); await refresh();
  }));
  form.append(actions);
  if (run.role === 'example') {
    renderPlaygroundTour(root, run, form);
    if (terminal) {
      const saved = el('details', undefined, 'pg-saved-takeaway'); saved.append(el('summary', 'Review your takeaway'), form); root.append(saved);
    }
    root.append(reference);
  } else root.append(form);
  if (run.activity.topic === 'integrity' || run.activity.difficulty === 'hard') renderPlaygroundCalculator(root);
  if (run.result) {
    const result = AscendFeedback.create({kind: run.result.passed ? 'success' : 'warning', label: run.result.passed ? 'PROGRESS SAVED' : 'EVIDENCE CHECK', title: run.result.passed ? run.role === 'example' ? 'Example complete. Put it into practice.' : 'Activity complete' : 'Keep investigating', message: run.role === 'example' && run.result.passed ? 'Your takeaway is saved. Apply what you learned in a fresh challenge.' : `${run.result.message}${run.result.xp ? ` +${run.result.xp} XP.` : ''}`});
    result.classList.add('pg-result', 'pg-completion');
    if (terminal && run.followup) {
      const next = el('div', undefined, 'pg-actions');
      const proceed = button(run.role === 'example' ? 'Try a separate challenge' : 'Try the changed case', async () => { await savePlaygroundDraft(); await startPlayground(await api(`playground/activities/${run.followup}`)); }, ''); proceed.append(icon('arrow')); next.append(proceed); $('.feedback-copy', result).append(next);
    }
    if (run.result.passed) title.after(result); else form.before(result);
  }
  if (run.debrief && run.role !== 'example') {
    const debrief = el('section', undefined, 'card pg-result'); debrief.append(el('h3', 'Why the evidence fits'), el('p', run.debrief));
    if (run.solution) playgroundData(debrief, run.solution); root.append(debrief);
  }
  const help = el('section', undefined, 'pg-help');
  if (!terminal) {
    if (run.hints_available) help.append(button('Use a limited hint', async () => { await savePlaygroundDraft(); await playgroundAction(run.id, 'hint'); await renderPlayground(); }));
    run.hint_text.forEach(text => help.append(el('p', text)));
    const examples = el('details'); examples.append(el('summary', 'Study a separate example'));
    run.activity.preparation.forEach(id => examples.append(button(id.replace('example-', 'Study '), async () => { await savePlaygroundDraft(true); await startPlayground(await api(`playground/activities/${id}`)); })));
    if (run.role !== 'example') help.append(examples);
    help.append(button('Report an environment problem', async () => {
      const current = capture(); current.environment_problem = true;
      await playgroundAction(run.id, 'save', {data: current}); playgroundDraft = null;
      notify('Work saved with an environment issue. No conceptual failure was recorded.', 'success'); await playgroundOpen('history');
    }, 'text-button'));
    help.append(button('End attempt', async () => {
      await savePlaygroundDraft(); await playgroundAction(run.id, 'end'); playgroundDraft = null; await renderPlayground();
    }, 'text-button'));
  }
  if (run.review_available && !run.revealed) help.append(button('Open solution review', async () => {
    await savePlaygroundDraft(); await playgroundAction(run.id, 'reveal'); await renderPlayground();
  }));
  root.append(help);
  if (terminal) {
    const actions = el('div', undefined, 'pg-actions');
    if (run.followup && !run.result) actions.append(button(run.role === 'example' ? 'Try a separate challenge' : 'Try the changed case', async () => startPlayground(await api(`playground/activities/${run.followup}`)), ''));
    actions.append(button(run.kind === 'challenge' ? 'Another challenge' : 'Another exercise', () => playgroundOpen(run.kind === 'challenge' ? 'challenges' : 'quick')),
      button('Back to track', async () => { await playgroundAction(run.id, 'returned'); await switchTab(state.overview?.mission ? 'path' : 'today'); }),
      button('Finish for today', async () => { await savePlaygroundDraft(true); await switchTab('today'); notify('Your activity is saved. See you next time.', 'success'); })); root.append(actions);
  }
  if (terminal || run.status === 'saved') renderPlaygroundFeedback(root, run);
}
function renderPlaygroundFeedback(root, run) {
  const section = el('details', undefined, 'pg-reference'); section.append(el('summary', 'How did this activity feel? (optional)'), el('p', 'Help tune future suggestions. These answers stay in your Ascend profile and do not affect XP or skill readiness.', 'small muted'));
  const form = el('form', undefined, 'pg-feedback'), previous = run.feedback || {};
  const minutes = playgroundField(form, 'Minutes actually working', previous.working_minutes ?? '', 'number'); minutes.min = 1; minutes.max = 1440; minutes.required = true;
  const setup = playgroundField(form, 'Extra setup minutes', previous.setup_minutes ?? 0, 'number'); setup.min = 0; setup.max = 1440;
  const difficulty = playgroundField(form, 'Difficulty felt', previous.difficulty || '', 'text', [['','Choose'],['too-easy','Too easy'],['about-right','About right'],['too-hard','Too hard']]); difficulty.required = true;
  const clarity = playgroundField(form, 'Was it clear what to do?', previous.clarity || '', 'text', [['','Choose'],['clear','Yes'],['unclear','No']]); clarity.required = true;
  const repetition = playgroundField(form, 'Did it feel fresh?', previous.repetition || '', 'text', [['','Choose'],['fresh','New to me'],['welcome-review','Useful review'],['unwanted-repeat','Unwanted repetition']]); repetition.required = true;
  const environment = playgroundField(form, 'Did a setup or technical problem get in the way?', previous.environment_issue ? 'yes':'no', 'text', [['no','No'],['yes','Yes']]);
  const note = playgroundField(form, 'Anything confusing or satisfying?', previous.note || '', 'textarea'); note.maxLength = 2000;
  const submit = el('button', 'Save feedback'); form.append(submit); form.addEventListener('submit', event => {
    event.preventDefault(); runAction(submit, async () => {
      await playgroundAction(run.id, 'feedback', {data:{working_minutes:Number(minutes.value), setup_minutes:Number(setup.value), difficulty:difficulty.value, clarity:clarity.value, repetition:repetition.value, environment_issue:environment.value === 'yes', note:note.value}});
      notify('Feedback saved. Your suggestions can now take it into account.', 'success'); section.open = false;
    });
  }); section.append(form); root.append(section);
}
function renderPlaygroundCalculator(root) {
  const section = el('details'); section.append(el('summary', 'SHA-256 text calculator'));
  const input = playgroundField(section, 'Exact text to hash (newlines count)', '', 'textarea');
  const output = el('output', '', 'pg-digest');
  section.append(button('Compute digest', async () => {
    const buffer = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(input.value));
    output.textContent = Array.from(new Uint8Array(buffer), x => x.toString(16).padStart(2, '0')).join('');
  }), output); root.append(section);
}
function renderPlaygroundWorkspace(root, run, work) {
  const editable = run.status === 'active';
  let workspace = structuredClone(work.workspace || run.data);
  const editor = el('div', undefined, 'pg-workspace');
  const observations = el('div', undefined, 'pg-observations'); observations.setAttribute('aria-live', 'polite');
  const isPolicy = !!workspace.policy;
  const renderEditor = () => {
    editor.replaceChildren();
    if (isPolicy) {
      const policies = el('fieldset'); policies.append(el('legend', 'Policy rules'));
      for (const [key, label] of Object.entries({deny_disabled: 'Deny disabled identities', owner_access: 'Allow owner read/write', admin_read: 'Allow admins to read', admin_write: 'Allow admins to write'})) {
        const wrap = el('label', undefined, 'check'), input = el('input'); input.type = 'checkbox'; input.checked = workspace.policy[key]; input.addEventListener('change', () => workspace.policy[key] = input.checked); wrap.append(input, document.createTextNode(label)); policies.append(wrap);
      }
      editor.append(policies);
    } else {
      playgroundField(editor, 'Filter marker (empty shows all)', workspace.marker).addEventListener('input', e => workspace.marker = e.target.value);
      playgroundField(editor, 'Minimum status', workspace.minimum_status, 'number').addEventListener('input', e => workspace.minimum_status = Number(e.target.value));
    }
    const rows = isPolicy ? workspace.requests : workspace.events;
    rows.forEach((row, index) => {
      const group = el('fieldset', undefined, 'pg-edit-row'); group.append(el('legend', `${isPolicy ? 'Request' : 'Event'} ${index+1}`));
      Object.entries(row).forEach(([key, value]) => {
        const options = key === 'enabled' ? [['true', 'Enabled'], ['false', 'Disabled']] : key === 'role' ? ['user', 'admin'] : key === 'action' ? ['read', 'write'] : null;
        playgroundField(group, key.replaceAll('_', ' '), value, key === 'status' ? 'number' : 'text', options).addEventListener('input', e => row[key] = key === 'enabled' ? e.target.value === 'true' : key === 'status' ? Number(e.target.value) : e.target.value);
      });
      group.append(button('Remove', () => { rows.splice(index, 1); renderEditor(); editor.dispatchEvent(new Event('input', {bubbles:true})); }, 'text-button')); editor.append(group);
    });
    editor.append(button(isPolicy ? 'Add request' : 'Add event', () => {
      rows.push(isPolicy ? {id:`r${rows.length+1}`, caller:'Ari', owner:'Ari', enabled:true, role:'user', action:'read'} : {id:`e${rows.length+1}`, time:'09:00:00', marker:'job', status:200}); renderEditor(); editor.dispatchEvent(new Event('input', {bubbles:true}));
    }));
  };
  renderEditor();
  if (!editable) editor.querySelectorAll('input, select, button').forEach(input => input.disabled = true);
  root.append(editor);
  const notes = playgroundField(root, 'What did you learn?', work.notes || '', 'textarea');
  const reminder = el('details'); reminder.append(el('summary', 'Leave a reminder for later (optional)'), el('p', 'A note to help you pick up this workspace next time.', 'small muted'));
  const next = playgroundField(reminder, 'When I return, I want to…', work.next_step || ''); root.append(reminder);
  const capture = () => ({...work, workspace, notes: notes.value, next_step: next.value});
  rememberPlayground(root, run, capture);
  const showObservations = rows => { observations.replaceChildren(el('h3', 'Observed results')); playgroundData(observations, rows); };
  showObservations(run.observations);
  const experiment = button('Run experiment', async () => { const result = await playgroundAction(run.id, 'experiment', {data: workspace}); showObservations(result.observations); }, '');
  experiment.disabled = !editable; root.append(experiment, observations);
  const actions = el('div', undefined, 'pg-actions');
  actions.append(button('Save workspace', async () => { await savePlaygroundDraft(true); notify('Workspace saved. Resume it from Saved work & history.', 'success'); await playgroundOpen('history'); }, ''));
  actions.append(button('Save learning log', async () => { await savePlaygroundDraft(); await playgroundAction(run.id, 'log', {learned: notes.value, next_step: next.value}); await refresh(); notify('Learning log saved.', 'success'); }));
  const copy = async options => {
    await savePlaygroundDraft(true);
    const sessions = await command(['session', 'status']);
    if (sessions.active && !options.end_scored) {
      const content = openSheet('Switch activity'); content.append(el('h2', 'End scored attempt and switch'), el('p', 'Creating a workspace copy stops the current scored track clock without completion or XP. Its original evidence stays saved.'));
      content.querySelector('h2').id = 'sheet-title';
      content.append(button('End scored attempt and switch', async () => { $('#sheet').close(); await copy({...options, end_scored:true}); }, ''), button('Cancel', () => $('#sheet').close())); return;
    }
    const result = await playgroundAction(run.id, 'copy', options); await refreshSessions(); await playgroundOpen(result.id);
  };
  actions.append(button('Duplicate workspace', () => copy({})), button('Reset into a new copy', () => copy({reset:true})), button('Start a blank copy', () => copy({blank:true})));
  if (isPolicy) actions.append(button('Introduce a hidden fault in a copy', () => copy({fault:true})));
  root.append(actions);
  if (run.hidden_fault) {
    root.append(el('p', 'One implementation rule differs from the displayed policy. Change requests and compare the owner, disabled and unrelated-user controls to find it.'));
    const rule = playgroundField(root, 'Rule to repair', '', 'text', [['', 'Choose a rule'], ['deny_disabled', 'Disabled identity check'], ['owner_access', 'Owner access'], ['admin_read', 'Admin read'], ['admin_write', 'Admin write']]);
    const repair = button('Repair and check controls', async () => {
      await savePlaygroundDraft();
      const result = await playgroundAction(run.id, 'repair', {rule: rule.value}); notify(result.message, result.repaired ? 'success' : 'error'); if (result.repaired) { await savePlaygroundDraft(); await renderPlayground(); }
    }); repair.disabled = !editable; root.append(repair);
    root.append(button('End investigation and reveal fault', async () => { await savePlaygroundDraft(true); await playgroundAction(run.id, 'end'); await playgroundAction(run.id, 'reveal'); await renderPlayground(); }, 'text-button'));
  }
  if (run.fault_rule) root.append(el('p', `Revealed rule: ${run.fault_rule.replaceAll('_', ' ')}. ${run.debrief}`));
  root.append(button('Back to track', async () => { await playgroundAction(run.id, 'returned'); await switchTab(state.overview?.mission ? 'path' : 'today'); }, 'text-button'));
  renderPlaygroundFeedback(root, run);
  if (isPolicy) {
    const link = el('a', 'Try the local HTTP lab setup', 'resource-link'); link.href = '#docs/lab-setup';
    root.append(el('p', 'For a separate HTTP lab running on your own machine, follow the setup guide. Keep observations in your workspace notes.', 'small muted'), link);
  }
}
