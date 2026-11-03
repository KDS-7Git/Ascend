"use strict";
let activeNotebook = null;

function notebookDraftKey(ref) { return `ascend-notes:${state.account?.username || 'local'}:${ref}`; }
function keepNotebookDraft(c) {
  try { localStorage.setItem(notebookDraftKey(c.ref), JSON.stringify({learned: c.learned.value, next_step: c.next.value, revision: c.work.revision})); } catch { /* The inline status still reports server save failures. */ }
}
async function flushChallengeNotebook(logProgress = false) {
  const c = activeNotebook;
  if (!c) return;
  clearTimeout(c.debounce);
  c.pending = c.pending.catch(() => {}).then(async () => {
    if (!c.dirty && !logProgress) return;
    const learned = c.learned.value, next_step = c.next.value;
    c.status.textContent = 'Saving…'; c.status.dataset.state = 'saving'; c.error.hidden = true;
    try {
      c.work = await api(`challenges/${encodeURIComponent(c.ref)}/notes`, {learned, next_step, revision: c.work.revision, log_progress: logProgress});
      c.dirty = learned !== c.learned.value || next_step !== c.next.value;
      c.status.textContent = c.dirty ? 'New changes waiting to save' : logProgress ? 'Progress saved' : 'All changes saved';
      c.status.dataset.state = c.dirty ? 'pending' : 'saved';
      if (!c.dirty) { try { localStorage.removeItem(notebookDraftKey(c.ref)); } catch {} }
      window.AscendMotion?.feedback?.(c.status, 'save');
    } catch (error) {
      keepNotebookDraft(c); c.status.textContent = 'Not saved to server'; c.status.dataset.state = 'error';
      c.error.textContent = `${error.message} Your text is kept in this browser.`; c.error.hidden = false;
      throw error;
    }
  });
  return c.pending;
}

async function openChallengeNotes(node) {
  const ref = `${node.pack_id}:${node.id}`;
  if (state.tab !== 'challenge' || state.challengeRef !== ref) await switchTab('challenge', {topic: ref});
  const c = activeNotebook;
  if (!c || c.ref !== ref) { notify('Start this challenge to open your notebook.'); return; }
  c.panel.open = true; c.panel.scrollIntoView({behavior: 'instant', block: 'nearest'}); c.learned.focus({preventScroll: true});
}

async function finishChallenge() {
  const c = activeNotebook; if (!c) return;
  c.panel.open = true;
  if (c.learned.value.trim().length < 20) {
    c.error.textContent = 'Add a short observation (at least 20 characters), then complete the lab.'; c.error.hidden = false;
    c.learned.focus(); return;
  }
  await flushChallengeNotebook();
  const previousStreak = state.overview?.current_streak || 0;
  const result = await api(`challenges/${encodeURIComponent(c.ref)}/complete`, {revision: c.work.revision});
  await refresh(); await renderChallenge();
  if (!result.already_completed) {
    showChallengeCelebration('Lab complete!', 'Your work is saved. Your track has moved forward.', state.overview?.current_streak > previousStreak);
  }
}

function showChallengeCelebration(title, text, streak = false) {
  const host = $('#challenge-content');
  host.querySelector('.lab-celebration')?.remove();
  const panel = el('section', undefined, 'lab-celebration'); panel.setAttribute('role', 'status');
  const mark = el('span', undefined, 'completion-mark'); mark.append(icon('check')); mark.setAttribute('aria-hidden', 'true');
  const copy = el('div'); copy.append(el('p', streak ? 'LAB COMPLETE · STREAK EXTENDED' : 'PROGRESS RECORDED', 'eyebrow'), el('h2', title), el('p', text));
  panel.append(mark, copy, button('Continue learning', () => switchTab('today'), '')); host.prepend(panel);
  window.AscendMotion?.feedback?.(panel, 'complete');
  if (streak) window.AscendMotion?.feedback?.($('#streak-chip') || $('#streak')?.parentElement, 'streak');
  panel.scrollIntoView({behavior: 'instant', block: 'nearest'});
}

async function prepareToEndChallenge() {
  const current = state.sessions?.active || state.sessions?.paused.at(-1); if (!current) return;
  const ref = `${current.pack_id}:${current.node_id}`;
  if (state.tab !== 'challenge' || state.challengeRef !== ref) await switchTab('challenge', {topic: ref});
  const c = activeNotebook;
  if (!c) return;
  c.panel.open = true; c.ending.open = true;
  c.ending.scrollIntoView({behavior: 'instant', block: 'nearest'});
  c.ending.querySelector('button')?.focus({preventScroll: true});
}

async function endChallengeWithoutCompletion() {
  await flushChallengeNotebook();
  await command(['session', 'end']); await refreshSessions(); await renderChallenge();
  notify('Session ended. Notes are saved; you can continue editing or complete the lab later.');
}

function mountChallengeNotebook(data) {
  activeNotebook = null;
  if (!data.work) return;
  const {node, work, session} = data, ref = `${node.pack_id}:${node.id}`, host = $('#challenge-content');
  const columns = el('div', undefined, 'lab-columns');
  const instructions = el('article', undefined, 'lab-instructions');
  instructions.append(...host.childNodes); columns.append(instructions); host.append(columns);
  const outline = el('nav', undefined, 'lab-outline'); outline.setAttribute('aria-label', 'In this lab');
  outline.append(el('p', 'IN THIS LAB', 'eyebrow'));
  const headings = [...instructions.querySelectorAll('h1, h2, h3')].filter(h => !h.closest('.doc-code')).slice(0, 8);
  headings.forEach((heading, i) => {
    if (!heading.id) heading.id = `lab-section-${i}`;
    const link = el('a', i ? heading.textContent : 'Overview'); link.href = `#${heading.id}`;
    link.addEventListener('click', event => { event.preventDefault(); heading.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start'}); });
    outline.append(link);
  });
  const notesLink = button('Notes & evidence', () => openChallengeNotes(node), 'text-button'); outline.append(notesLink);
  columns.prepend(outline);

  const panel = el('details', undefined, 'lab-notebook'); panel.id = 'lab-notebook'; panel.open = innerWidth >= 1100;
  const summary = el('summary'); summary.append(icon('book'), el('span', 'Notes & evidence')); panel.append(summary);
  const body = el('div', undefined, 'notebook-body'); panel.append(body);
  const status = el('p', work.saved_at ? 'Saved notes restored' : 'Your notes save as you write', 'notebook-status'); status.setAttribute('role', 'status'); body.append(status);
  const learned = field(body, 'learned', 'Your notes', 'textarea', work.learned); learned.maxLength = 10000; learned.rows = 7; learned.placeholder = 'What did you try? What did you observe?';
  const next = field(body, 'next-step', 'Next step', 'text', work.next_step); next.maxLength = 4000;
  const error = el('p', '', 'error notebook-error'); error.setAttribute('role', 'alert'); error.hidden = true; body.append(error);
  const c = {ref, node, panel, learned, next, status, error, work, dirty: false, pending: Promise.resolve()}; activeNotebook = c;
  try {
    const local = JSON.parse(localStorage.getItem(notebookDraftKey(ref)) || 'null');
    if (local && (local.learned !== work.learned || local.next_step !== work.next_step)) {
      learned.value = local.learned; next.value = local.next_step; c.dirty = true;
      // Keep the revision used by this draft; stale drafts must conflict, not overwrite.
      c.work = {...work, revision: local.revision}; status.textContent = 'Unsaved browser draft restored'; status.dataset.state = 'pending';
    }
  } catch { /* Saved server notes remain available. */ }
  const changed = () => {
    c.dirty = true; keepNotebookDraft(c); status.textContent = 'Unsaved changes'; status.dataset.state = 'pending';
    clearTimeout(c.debounce); c.debounce = setTimeout(() => { if (activeNotebook === c) flushChallengeNotebook().catch(() => {}); }, 650);
  };
  learned.addEventListener('input', changed); next.addEventListener('input', changed);
  const save = button('Save progress', async () => {
    await flushChallengeNotebook(true); const before = state.overview?.current_streak || 0; await refresh();
    if ((state.overview?.current_streak || 0) > before) window.AscendMotion?.feedback?.($('#streak')?.parentElement, 'streak');
    notify('Progress saved. Keep adding to these notes whenever you return.', 'success');
  }, 'secondary'); body.append(save);
  const recovery = el('details', undefined, 'quiet-details'); recovery.append(el('summary', 'Note history & recovery'));
  recovery.append(button('Download my notes', () => downloadNotebook(learned.value, `${node.id}-notes.txt`), 'text-button'));
  recovery.append(button('Load latest saved notes', async () => {
    const latest = (await api(`challenges/${encodeURIComponent(ref)}`)).work;
    if (c.dirty) downloadNotebook(learned.value, `${node.id}-unsaved-notes.txt`);
    clearTimeout(c.debounce); await c.pending.catch(() => {}); c.work = latest; learned.value = latest.learned; next.value = latest.next_step; c.dirty = false;
    try { localStorage.removeItem(notebookDraftKey(ref)); } catch {} status.textContent = 'Saved notes restored'; error.hidden = true;
  }, 'text-button'));
  for (const entry of work.history) {
    const row = el('details'); row.append(el('summary', `${entry.day} · ${entry.complete ? 'Completed' : 'Progress note'}`), el('p', entry.learned, 'saved-note-text')); recovery.append(row);
  }
  body.append(recovery);

  if (work.upload_allowed) {
    const evidence = el('section', undefined, 'notebook-evidence'); evidence.append(el('h3', 'Your evidence'), el('p', `Save ${work.expected_filename} on your computer, then upload it here. Up to 8 MB.`, 'field-help'));
    const upload = el('input'); upload.type = 'file'; upload.id = 'lab-evidence-upload'; upload.setAttribute('aria-label', 'Upload evidence');
    const feedback = el('div', work.attachment ? `${work.attachment.name} · saved` : 'No file uploaded yet', 'field-help'); feedback.setAttribute('role', 'status');
    upload.addEventListener('change', async () => {
      const file = upload.files[0]; if (!file) return;
      if (file.size > work.max_upload_bytes) { feedback.textContent = 'Choose a file up to 8 MB.'; return; }
      const form = new FormData(); form.append('file', file); upload.disabled = true; evidence.setAttribute('aria-busy', 'true');
      AscendFeedback.set(feedback, {kind: 'info', title: 'Uploading and checking…', compact: true});
      try {
        await flushChallengeNotebook(); const result = await api(`challenges/${encodeURIComponent(ref)}/evidence`, form);
        c.work = {...c.work, attachment: result.work.attachment};
        AscendFeedback.set(feedback, {kind: 'success', title: 'File saved · evidence accepted', message: file.name, compact: true}); feedback.dataset.state = 'saved';
        download.hidden = false; window.AscendMotion?.feedback?.(feedback, 'save');
      } catch (err) { AscendFeedback.set(feedback, {kind: 'error', title: 'Upload needs attention', message: err.message, compact: true}); feedback.dataset.state = 'error'; }
      finally { upload.disabled = false; evidence.removeAttribute('aria-busy'); }
    });
    const download = button('Download saved evidence', async () => {
      const response = await fetch(`/api/challenges/${encodeURIComponent(ref)}/evidence`, {headers: state.token ? {Authorization: `Bearer ${state.token}`} : {}, cache: 'no-store'});
      if (!response.ok) throw new Error('The attachment could not be downloaded.');
      downloadNotebook(await response.blob(), c.work.attachment?.name || work.expected_filename);
    }, 'text-button'); download.hidden = !work.attachment;
    evidence.append(upload, feedback, download); body.append(evidence);
  }
  if (node.verify?.type !== 'lab') {
    const checks = el('div', '', 'field-help'); checks.setAttribute('role', 'status');
    if (node.verify?.type !== 'manual') body.append(button('Check evidence', async () => {
      const result = await api(`challenges/${encodeURIComponent(ref)}/check`, {});
      AscendFeedback.set(checks, {kind: result.ok ? 'success' : 'error', title: result.ok ? 'Evidence ready' : 'Check your evidence', message: result.ok ? 'Complete the lab below to advance your track.' : result.summary, compact: true});
      window.AscendMotion?.feedback?.(checks, result.ok ? 'save' : 'error');
    }, 'text-button'), checks);
    body.append(el('p', 'Complete only when you have met the finish line. An artifact check does not grade your reasoning.', 'field-help'));
    body.append(button(node.status === 'done' ? 'Continue learning' : 'Complete lab', node.status === 'done' ? () => switchTab('today') : finishChallenge, 'notebook-complete'));
    if (session?.status === 'finished') body.append(button('Practice again', async () => {
      await flushChallengeNotebook(); await api(`challenges/${encodeURIComponent(ref)}/practice`, {minutes: node.estimate});
      await refreshSessions(); await renderChallenge(); notify('Practice started. Your original attempt is kept; this practice does not earn additional XP.', 'success');
      window.AscendMotion?.feedback?.($('#task-session'), 'start');
    }, 'text-button'));
  }
  const ending = el('details', undefined, 'notebook-end'); ending.append(el('summary', 'Finish this session'));
  ending.append(el('p', 'Use Complete lab above to advance the track. Ending only stops the clock; your notes remain editable.', 'field-help'), button('End session without completing', endChallengeWithoutCompletion, 'text-button'));
  ending.hidden = !['running', 'paused'].includes(session?.status); body.append(ending); c.ending = ending;
  columns.append(panel);
  const toolbar = el('div', undefined, 'lab-toolbar');
  toolbar.append(el('span', node.status === 'done' ? '✓ Completed · notes remain editable' : session?.status === 'finished' ? 'Session ended · continue your work below' : work.practice ? 'Practice session · no additional XP' : 'Lab in progress', 'lab-state'), button('Notes & evidence', () => openChallengeNotes(node), 'text-button'));
  if (node.status !== 'done' && node.verify?.type !== 'lab') toolbar.append(button('Complete lab', finishChallenge, ''));
  instructions.querySelector('h1')?.after(toolbar);
}

function downloadNotebook(value, name) {
  const blob = value instanceof Blob ? value : new Blob([value], {type: 'text/plain;charset=utf-8'});
  const url = URL.createObjectURL(blob), link = document.createElement('a'); link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
