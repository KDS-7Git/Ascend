"use strict";
const historyLibraryState = {search: '', status: '', sort: 'recent', page: 0};
const workDate = value => {
  try { return new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short', timeZone: state.account?.settings?.timezone}).format(new Date(value)); }
  catch { return value.slice(0, 16).replace('T', ' '); }
};
const workOpen = run => ['active', 'saved'].includes(run.status);
function workStatus(run) {
  return run.status === 'active' ? 'In progress' : run.status === 'saved' ? 'Saved' : run.status === 'passed' ? run.role === 'example' ? 'Studied' : 'Completed' : 'Ended';
}
function historyWorkRow(run, number) {
  const open = workOpen(run), row = el('li', undefined, 'work-row'); row.dataset.status = run.status; row.dataset.runId = run.id;
  const emblem = el('span', undefined, 'work-emblem'); emblem.append(icon(open ? 'book' : run.status === 'passed' ? 'check' : 'flag'));
  const copy = el('div', undefined, 'work-copy'); copy.append(el('h3', `Attempt ${number}`), el('p', `${workDate(run.created_at)} · version ${run.version}`, 'small muted'));
  const meta = el('div', undefined, 'work-meta'); meta.append(el('span', workStatus(run), 'work-status'), el('span', `${Math.floor(run.elapsed_seconds / 60)} min${run.strict_timer && open ? ' · timer running' : ' practiced'}${run.result?.xp ? ` · +${run.result.xp} XP` : ''}`, 'small muted'));
  const label = open ? run.strict_timer ? 'Return to challenge' : 'Resume' : 'Review';
  const action = button(label, () => open ? resumePlayground(run) : playgroundOpen(run.id), open ? '' : 'text-button');
  action.setAttribute('aria-label', `${label} ${run.title}, attempt ${number}`); row.append(emblem, copy, meta, action); return row;
}
function renderHistoryLibrary(root, runs) {
  const preferences = historyLibraryState, perPage = 10, grouped = new Map();
  for (const run of runs) { if (!grouped.has(run.activity_id)) grouped.set(run.activity_id, []); grouped.get(run.activity_id).push(run); }
  const groups = [...grouped].map(([id, attempts]) => {
    attempts.sort((a, b) => b.updated_at.localeCompare(a.updated_at) || b.created_at.localeCompare(a.created_at));
    return {id, attempts, latest: attempts[0], title: attempts[0].title};
  });
  root.append(el('h2', 'Saved work & history'), el('p', 'Each activity appears once. Open its group to see all attempts and return to saved work.', 'muted'));
  const tools = el('div', undefined, 'work-tools'), search = playgroundField(tools, 'Search saved work', preferences.search, 'search'); search.placeholder = 'Search by title or activity';
  const matches = (run, value) => !value || (value === 'open' ? workOpen(run) : run.status === value);
  const count = value => groups.filter(g => g.attempts.some(r => matches(r, value))).length;
  const status = playgroundField(tools, 'Show', preferences.status, 'text', [['', `All activities (${groups.length})`], ['open', `In progress (${count('open')})`], ['passed', `Completed / studied (${count('passed')})`], ['ended', `Ended (${count('ended')})`]]);
  const sort = playgroundField(tools, 'Sort by', preferences.sort, 'text', [['recent', 'Recently updated'], ['oldest', 'Oldest first'], ['title', 'Title A–Z']]);
  const summary = el('p', '', 'work-count'); summary.setAttribute('role', 'status');
  const list = el('ol', undefined, 'work-list'); list.setAttribute('aria-label', 'Saved activity groups'); list.tabIndex = -1;
  const pages = el('nav', undefined, 'work-pagination'); pages.setAttribute('aria-label', 'Saved work pages'); root.append(tools, summary, list, pages);
  function draw(focus = false) {
    const query = preferences.search.trim().toLowerCase();
    const found = groups.filter(g => g.attempts.some(r => (!query || `${r.title} ${r.activity_id}`.toLowerCase().includes(query)) && matches(r, preferences.status)));
    found.sort((a, b) => preferences.sort === 'title' ? a.title.localeCompare(b.title) : preferences.sort === 'oldest' ? a.latest.updated_at.localeCompare(b.latest.updated_at) : b.latest.updated_at.localeCompare(a.latest.updated_at));
    const totalPages = Math.max(1, Math.ceil(found.length / perPage)); preferences.page = Math.min(preferences.page, totalPages - 1);
    list.replaceChildren(); pages.replaceChildren();
    const totalAttempts = found.reduce((n, g) => n + g.attempts.length, 0);
    summary.textContent = `${found.length} ${found.length === 1 ? 'activity' : 'activities'} · ${totalAttempts} ${totalAttempts === 1 ? 'attempt' : 'attempts'}${found.length > perPage ? ` · ${preferences.page * perPage + 1}–${Math.min(found.length, (preferences.page + 1) * perPage)} shown` : ''}`;
    for (const group of found.slice(preferences.page * perPage, (preferences.page + 1) * perPage)) {
      const matching = group.attempts.filter(r => matches(r, preferences.status));
      const display = matching.find(workOpen) || matching.find(r => r.status === 'passed') || matching[0];
      const row = el('li', undefined, 'work-row work-group-row'); row.dataset.status = display.status; row.dataset.activityId = group.id;
      const emblem = el('span', undefined, 'work-emblem'); emblem.append(icon(workOpen(display) ? 'book' : display.status === 'passed' ? 'check' : 'flag'));
      const title = el('h3'), groupLink = el('a', group.title); groupLink.href = `#attempts/${encodeURIComponent(group.id)}`; title.append(groupLink);
      const copy = el('div', undefined, 'work-copy'); copy.append(title, el('p', `${group.attempts.length} ${group.attempts.length === 1 ? 'attempt' : 'attempts'} · updated ${workDate(group.latest.updated_at)}`, 'small muted'));
      const meta = el('div', undefined, 'work-meta'); meta.append(el('span', workStatus(display), 'work-status'));
      const complete = group.attempts.filter(r => r.status === 'passed').length;
      if (complete) meta.append(el('span', `${complete} ${display.role === 'example' ? 'studied' : 'completed'}`, 'small muted'));
      const action = button('View attempts', () => switchTab('attempts', {topic: group.id}), 'text-button'); action.setAttribute('aria-label', `View all ${group.attempts.length} attempts for ${group.title}`);
      row.append(emblem, copy, meta, action); list.append(row);
    }
    if (!found.length) {
      const empty = el('li', undefined, 'work-empty'); empty.append(icon('book'), el('h3', runs.length ? 'No matching work' : 'Your next attempt starts here'), el('p', runs.length ? 'Try another title or show all work.' : 'Start an activity and its saved work will appear here.', 'muted'));
      empty.append(button(runs.length ? 'Clear filters' : 'Find an activity', () => { if (!runs.length) return playgroundOpen('quick'); search.value = ''; status.value = ''; Object.assign(preferences, {search: '', status: '', page: 0}); draw(); search.focus(); }, 'text-button')); list.append(empty);
    }
    if (totalPages > 1) {
      const previous = button('Previous', () => { preferences.page--; draw(true); }); previous.disabled = preferences.page === 0;
      const next = button('Next', () => { preferences.page++; draw(true); }); next.disabled = preferences.page === totalPages - 1; pages.append(previous, el('span', `Page ${preferences.page + 1} of ${totalPages}`, 'small muted'), next);
    }
    if (focus) { list.focus({preventScroll:true}); tools.scrollIntoView({block:'start', behavior:'instant'}); }
  }
  search.addEventListener('input', () => { preferences.search = search.value; preferences.page = 0; draw(); });
  status.addEventListener('change', () => { preferences.status = status.value; preferences.page = 0; draw(); });
  sort.addEventListener('change', () => { preferences.sort = sort.value; preferences.page = 0; draw(); }); draw();
}
async function renderAttemptGroup() {
  const id = state.attemptGroupRef, root = $('#attempts-content'); root.replaceChildren();
  const history = await api('playground/history');
  if (state.tab !== 'attempts' || state.attemptGroupRef !== id) return;
  const runs = history.filter(r => r.activity_id === id).reverse().sort((a, b) => a.created_at.localeCompare(b.created_at));
  if (!runs.length) throw new Error('No saved attempts for this activity.');
  const title = el('h1', runs.at(-1).title); title.id = 'attempt-group-title';
  root.append(el('p', 'Saved work & history', 'eyebrow'), title, el('p', `${runs.length} ${runs.length === 1 ? 'attempt' : 'attempts'}. Open one to continue or review its result.`, 'muted'));
  const list = el('ol', undefined, 'work-list'); list.setAttribute('aria-label', 'Activity attempts');
  runs.map((run, i) => historyWorkRow(run, i + 1)).reverse().forEach(row => list.append(row)); root.append(list);
  document.title = `${title.textContent} attempts · Ascend`;
}
