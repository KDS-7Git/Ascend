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
function historyWorkRow(run) {
  const open = workOpen(run), row = el('li', undefined, 'work-row'); row.dataset.status = run.status; row.dataset.runId = run.id;
  const emblem = el('span', undefined, 'work-emblem'); emblem.append(icon(open ? 'book' : run.status === 'passed' ? 'check' : 'flag'));
  const copy = el('div', undefined, 'work-copy'); copy.append(el('h3', run.title), el('p', workDate(run.updated_at), 'small muted'));
  const meta = el('div', undefined, 'work-meta'); meta.append(el('span', workStatus(run), 'work-status'), el('span', `${Math.floor(run.elapsed_seconds / 60)} min practiced${run.result?.xp ? ` · +${run.result.xp} XP` : ''}`, 'small muted'));
  const action = button(open ? 'Resume' : 'Review', () => open ? resumePlayground(run) : playgroundOpen(run.id), open ? '' : 'text-button');
  action.setAttribute('aria-label', `${open ? 'Resume' : 'Review'} ${run.title}`); row.append(emblem, copy, meta, action); return row;
}
function renderHistoryLibrary(root, runs) {
  const preferences = historyLibraryState, perPage = 10;
  root.append(el('h2', 'Saved work & history'), el('p', 'Return to saved answers, notes and experiments, or review a finished activity.', 'muted'));
  const tools = el('div', undefined, 'work-tools'), search = playgroundField(tools, 'Search saved work', preferences.search, 'search'); search.placeholder = 'Search by title or activity';
  const matches = (run, value) => !value || (value === 'open' ? workOpen(run) : run.status === value);
  const count = value => runs.filter(r => matches(r, value)).length;
  const status = playgroundField(tools, 'Show', preferences.status, 'text', [['', `All work (${runs.length})`], ['open', `In progress (${count('open')})`], ['passed', `Completed / studied (${count('passed')})`], ['ended', `Ended (${count('ended')})`]]);
  const sort = playgroundField(tools, 'Sort by', preferences.sort, 'text', [['recent', 'Recently updated'], ['oldest', 'Oldest first'], ['title', 'Title A–Z']]);
  const summary = el('p', '', 'work-count'); summary.setAttribute('role', 'status');
  const list = el('ol', undefined, 'work-list'); list.setAttribute('aria-label', 'Saved activities'); list.tabIndex = -1;
  const pages = el('nav', undefined, 'work-pagination'); pages.setAttribute('aria-label', 'Saved work pages'); root.append(tools, summary, list, pages);
  function draw(focus = false) {
    const query = preferences.search.trim().toLowerCase();
    const found = runs.filter(r => (!query || `${r.title} ${r.activity_id}`.toLowerCase().includes(query)) && matches(r, preferences.status));
    found.sort((a, b) => preferences.sort === 'title' ? a.title.localeCompare(b.title) : preferences.sort === 'oldest' ? a.updated_at.localeCompare(b.updated_at) : b.updated_at.localeCompare(a.updated_at));
    const totalPages = Math.max(1, Math.ceil(found.length / perPage)); preferences.page = Math.min(preferences.page, totalPages - 1);
    list.replaceChildren(); pages.replaceChildren();
    summary.textContent = `${found.length} saved activities${found.length > perPage ? ` · ${preferences.page * perPage + 1}–${Math.min(found.length, (preferences.page + 1) * perPage)} shown` : ''}`;
    found.slice(preferences.page * perPage, (preferences.page + 1) * perPage).forEach(run => list.append(historyWorkRow(run)));
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
