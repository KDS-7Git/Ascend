"use strict";
const labLocation = {'local-files': 'Files', 'local-container': 'Containers', 'local-vm': 'Linux VM', 'local-cluster': 'Dedicated cluster', cloud: 'Cloud account', external: 'External service'};
const labBriefs = {
  'linux-upskill': 'Build confidence with Linux commands, services and system administration.',
  labtainers: 'Practice networking in guided Linux environments with saved observations.',
  vampi: 'Compare API permissions and investigate access to another user’s objects.',
  'restaurant-api': 'Repair an API profile and compare allowed requests with denied controls.',
  wrongsecrets: 'Find exposed secrets and compare corrected configurations.',
  stratocyberlab: 'Explore a Linux cyber range in a dedicated environment.',
  'security-datasets': 'Investigate a real Linux audit trail and separate observation from intent.',
  'evtx-samples': 'Investigate Windows event samples with Linux analysis tools.',
  kc7: 'Explore investigation datasets and ask questions of security events.',
  'bgp-labs': 'Establish BGP sessions, protect peers and repair route export policies.',
  'rpisec-mbe': 'Study binary behavior and reversing in a dedicated compatibility VM.',
  cloudfoxable: 'Investigate cloud permissions and access to a training secret.',
  'kubernetes-goat': 'Compare Kubernetes permissions in a disposable training cluster.',
  'mastg-playground': 'Investigate Android storage and compare app access boundaries.',
  'vulnerable-llm-agent': 'Compare normal and injected agent requests against synthetic transactions.'
};
const labFilters = {search: '', level: '', location: ''};
const labBytes = bytes => bytes >= 1073741824 ? `${(bytes / 1073741824).toFixed(1)} GiB` : bytes < 1048576 ? `${(bytes / 1024).toFixed(1)} KiB` : `${(bytes / 1048576).toFixed(1)} MiB`;
function labLink(label, url) {
  const a = el('a', label, 'resource-link'); a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; return a;
}
function labRouteLink(label, id, className = 'resource-link') {
  const a = el('a', label, className); a.href = `#lab/${encodeURIComponent(id)}`; return a;
}
function labReferenceCard(lab) {
  const card = el('article', undefined, 'card pg-catalog-card pg-lab'); card.dataset.role = 'challenge';
  const emblem = el('div', undefined, 'pg-emblem'); emblem.append(icon('layers')); card.append(emblem);
  card.append(el('p', `${lab.levels.join(' / ')} · ${labLocation[lab.location]}`, 'eyebrow'), el('h2', lab.title), el('p', labBriefs[lab.id] || lab.delivery));
  const ready = lab.recipes.filter(r => r.runnable).length;
  const managed = lab.recipes.some(r => r.local_workflow);
  card.append(el('p', ready ? `${ready} ready ${ready === 1 ? 'exercise' : 'exercises'}` : managed ? 'Guided setup & evidence' : 'Reference · setup under review', 'pg-card-promise'));
  const actions = el('div', undefined, 'pg-actions'); actions.append(labRouteLink('Open lab', lab.id, 'primary-link')); card.append(actions); return card;
}
function trackLabReferences(refs) {
  if (!refs.length) return null;
  const details = el('details', undefined, 'page-section'); details.append(el('summary', `Open-source labs (${refs.length})`));
  const list = el('div', undefined, 'pg-catalog'); list.append(...refs.map(labReferenceCard)); details.append(list); return details;
}
async function renderLabCatalog(root) {
  const [labs, attempts] = await Promise.all([api('lab-catalog'), api('lab-attempts')]);
  if (!root.isConnected || state.tab !== 'playground' || state.playgroundRoute !== 'labs') return;
  root.append(el('h2', 'Linux labs'), el('p', 'Choose an exercise to investigate or experiment. Open a lab for its task, setup and saved work.'));
  const form = el('div', undefined, 'pg-filters');
  const query = playgroundField(form, 'Search labs', labFilters.search, 'search');
  const advanced = el('details', undefined, 'pg-advanced'); advanced.append(el('summary', 'More filters'));
  const extra = el('div', undefined, 'pg-filters'); advanced.append(extra);
  const level = playgroundField(extra, 'Lab level', labFilters.level, 'text', [['', 'All levels'], 'starter', 'intermediate', 'advanced']);
  const location = playgroundField(extra, 'Runs on', labFilters.location, 'text', [['', 'All environments'], ...Object.entries(labLocation)]); form.append(advanced);
  const shelf = el('section', undefined, 'pg-shelf'), count = el('p', '', 'small muted'); count.setAttribute('aria-live', 'polite');
  const list = el('div', undefined, 'pg-catalog');
  function draw() {
    Object.assign(labFilters, {search: query.value, level: level.value, location: location.value});
    const rows = labs.filter(l => (!level.value || l.levels.includes(level.value)) && (!location.value || l.location === location.value || l.recipes.some(r => r.location === location.value)) && JSON.stringify(l).toLowerCase().includes(query.value.trim().toLowerCase()));
    count.textContent = `${rows.length} ${rows.length === 1 ? 'lab' : 'labs'}`; list.replaceChildren(...rows.map(labReferenceCard));
    if (!rows.length) list.append(el('p', 'No labs match these filters.'));
  }
  [query, level, location].forEach(input => input.addEventListener('input', draw));
  shelf.append(count, list); root.append(form, shelf); draw();
  if (attempts.length) {
    const history = el('details', undefined, 'quiet-details'); history.append(el('summary', 'Local lab results & sessions'));
    for (const attempt of attempts) {
      const card = el('article', undefined, 'card'); card.append(labRouteLink(attempt.recipe_id, attempt.recipe_id), el('p', `${attempt.status} · ${attempt.origin === 'offline' ? 'Synchronized offline practice' : 'Online session'}`));
      if (attempt.result) {
        const result = AscendFeedback.create({kind: attempt.result.status === 'pass' ? 'success' : 'warning', title: `${attempt.result.evidence_label}: ${attempt.result.status}`, message: attempt.result.detail || '', compact: true});
        window.AscendRewards?.decorate(result, {kind: 'answer', positive: attempt.result.status === 'pass', practice: attempt.result.practice_reward, evidence: 'Practice points for your recorded work.'}); card.append(result);
      }
      else card.append(el('p', 'Finish or destroy on the computer that started this lab. Stopping compute keeps the session reserved.', 'small')); history.append(card);
    }
    root.append(history);
  }
  const help = el('a', 'Setup, offline work & cleanup', 'resource-link'); help.href = '#docs/linux-labs'; root.append(help);
}
function labSection(title) { const section = el('section', undefined, 'page-section'); section.append(el('h2', title)); return section; }
function labLocalWorkflow(recipe) {
  const setup = el('details', undefined, 'lab-local-setup'); setup.append(el('summary', 'Run on your own Linux computer'));
  if (recipe.runnable) {
    setup.append(el('pre', `ascend local-lab doctor ${recipe.id}\nascend local-lab start ${recipe.id}`, 'pg-text-evidence'), el('p', 'Replace RUN with the run ID returned by start. Downloads and saved work stay on the computer running the lab.', 'small'));
    const m = recipe.measurements;
    setup.append(el('p', `${m.download_scope ? 'First-download budget' : 'Measured download'}: ${labBytes(m.download_bytes)} · observed peak disk: ${labBytes(m.peak_disk_bytes)} · tested: ${recipe.tested_platforms.join(', ')}`, 'small muted'));
    setup.append(el('pre', 'ascend local-lab show RUN\nascend local-lab check RUN\nascend local-lab stop RUN\nascend local-lab resume RUN\nascend local-lab export RUN\nascend local-lab finish RUN\nascend local-lab sync RUN', 'pg-text-evidence'));
  } else if (recipe.evidence_reviewed) {
    setup.append(el('p', 'Prepare pinned references and the evidence workspace, then follow the saved setup plan on your PC, VM, cluster or configured account.'));
    setup.append(el('pre', `ascend local-lab prepare ${recipe.id}\nascend local-lab show RUN\nascend local-lab observe RUN ARTIFACT\nascend local-lab capture RUN ARTIFACT observation.json\nascend local-lab check RUN\nascend local-lab finish RUN\nascend local-lab sync RUN`, 'pg-text-evidence'));
    setup.append(el('p', 'The workspace supplies artifact templates and exact setup instructions. Checks interpret submitted observations and their negative controls.', 'small'));
    setup.append(el('pre', `ascend lab plan ${recipe.id}\nascend local-lab record ${recipe.id} report.json`, 'pg-text-evidence'));
  }
  return setup;
}
async function renderLabDetail() {
  const id = state.labRef, root = $('#lab-content'); root.replaceChildren();
  const data = await api(`lab-catalog/${encodeURIComponent(id)}`);
  if (state.tab !== 'lab' || state.labRef !== id) return;
  const lab = data.reference || data;
  const recipes = data.reference ? (await api(`lab-catalog/${encodeURIComponent(lab.id)}`)).recipes : data.recipes;
  if (state.tab !== 'lab' || state.labRef !== id) return;
  const recipe = data.reference ? data : recipes[0];
  const header = el('header', undefined, 'page-header'), heading = el('div'), title = el('h1', lab.title); title.id = 'lab-title';
  heading.append(el('p', `Linux labs · ${lab.levels.join(' / ')}`, 'eyebrow'), title, el('p', labBriefs[lab.id] || lab.delivery, 'muted')); header.append(heading); root.append(header);
  document.title = `${recipe ? recipe.title : lab.title} · Ascend`;
  if (recipes.length > 1) {
    const choices = el('nav', undefined, 'lab-exercises'); choices.setAttribute('aria-label', 'Lab exercises');
    for (const r of recipes) { const a = labRouteLink(r.title, r.id); if (r.id === recipe.id) a.setAttribute('aria-current', 'page'); choices.append(a); } root.append(choices);
  }
  if (recipe) {
    const task = labSection('Your task'); task.append(el('h3', recipe.title), el('p', recipe.objective || recipe.check_meaning || lab.delivery));
    if (recipe.instructions) task.append(el('p', recipe.instructions));
    if (!recipe.runnable) task.append(el('p', recipe.availability_reason || 'Runtime setup is still under review.', 'small muted')); root.append(task);
    const execution = labSection('Run this lab'), server = el('div', undefined, 'lab-server'); execution.append(server);
    if (recipe.runnable || recipe.evidence_reviewed) execution.append(labLocalWorkflow(recipe)); root.append(execution);
    const evidence = labSection('Evidence & saved work'); evidence.append(el('p', recipe.evidence_label || 'Learner-submitted observations'), el('p', 'Local artifacts are learner-controlled, award no XP and do not complete verified track milestones. Server checks describe only the behavior they actually observe.', 'small muted')); root.append(evidence);
    await renderHostedLab(server, recipe);
  } else root.append(el('p', 'This reference has no integrated exercise yet. Review preparation and upstream instructions before choosing an environment.', 'card'));
  if (state.tab !== 'lab' || state.labRef !== id) return;
  const source = el('details', undefined, 'page-section lab-source'); source.append(el('summary', 'Source, requirements & verification'));
  source.append(el('p', `Preparation: ${lab.prerequisites.join('; ')}`), el('p', lab.delivery), labLink('Upstream repository', lab.repository), el('p', `License: ${lab.license.identifier}`), el('p', `Reviewed source: ${recipe?.source?.revision || lab.reviewed_revision || 'Not yet pinned for execution'}`, 'small'));
  if (recipe?.license_review) source.append(el('p', recipe.license_review, 'small'));
  source.append(el('p', lab.upstream_verification), el('p', `Research notes: ${lab.limits}`, 'small muted'), el('p', 'Levels follow prerequisites and are not calibrated across repositories.', 'small muted')); root.append(source);
}

let hostedPoll;
const hostedDrafts = new Map();
const hostedConsoleDrafts = new Map();
async function renderHostedLab(root, recipe) {
  clearTimeout(hostedPoll);
  let capabilities;
  try { capabilities = await api('hosted-labs/capabilities'); }
  catch (error) {
    root.append(el('p', error.message, 'small muted'), button('Retry server connection', () => { root.replaceChildren(); return renderHostedLab(root, recipe); }, 'text-button')); return;
  }
  if (!root.isConnected || state.tab !== 'lab') return;
  if (!capabilities.configured) { root.append(el('p', 'Server labs will be available here when this installation’s server is connected. You can use the local setup below.', 'small muted')); return; }
  if (!capabilities.recipes.includes(recipe.id)) { root.append(el('p', 'This exercise needs its own environment setup. Review the local plan below; browser launch is not available for it yet.', 'small muted')); return; }
  const ref = state.labRef, account = state.account?.username;
  let lastSignature, lastJob;
  const selectedFiles = new Map();
  const current = () => root.isConnected && state.tab === 'lab' && state.labRef === ref && state.account?.username === account;
  async function submit(action, run, data = {}) {
    const path = action === 'start' ? 'hosted-labs/runs' : `hosted-labs/runs/${run.id}/${action}`;
    const job = await api(path, action === 'start' ? {recipe_id: recipe.id} : data);
    lastJob = job.id; lastSignature = null; await refresh();
  }
  function download(value, name) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], {type: 'application/json'}));
    const a = el('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function draw(data) {
    root.replaceChildren(); root.append(el('h3', 'Run on the server'));
    const busy = data.job && ['queued', 'running'].includes(data.job.status);
    const status = el('p', busy ? `${data.job.action === 'start' ? 'Preparing your lab' : 'Working'}… You can leave this page and return.` : 'Work in your browser. The server keeps the lab files and downloads.', 'small'); status.setAttribute('role', 'status'); root.append(status);
    const runs = data.runs.filter(r => r.recipe_id === recipe.id);
    const run = runs.find(r => r.status !== 'destroyed') || runs.at(-1);
    const active = data.runs.find(r => r.status !== 'destroyed');
    if (data.job?.status === 'failed') root.append(el('p', data.job.error, 'small lab-server-output'));
    if (data.job?.result && data.job.run_id === run?.id && ['http', 'router', 'check'].includes(data.job.action)) {
      root.append(el('pre', typeof data.job.result.output === 'string' ? data.job.result.output : JSON.stringify(data.job.result, null, 2), 'pg-text-evidence lab-server-output'));
    }
    if (!run || run.status === 'destroyed') {
      if (active) root.append(el('p', `Your ${active.title} lab is ${active.status}. Finish or destroy it before starting another.`), labRouteLink('Open your active lab', active.recipe_id));
      else { const start = button(run ? 'Start a new server lab' : 'Launch on server', () => submit('start'), ''); start.disabled = busy; root.append(start); }
    }
    if (!run) return;
    root.append(el('p', `${run.status} · deadline ${new Date(run.expires_at * 1000).toLocaleString()}`, 'small muted'));
    if (run.cleanup_error) root.append(el('p', run.cleanup_error, 'small'));
    const actions = el('div', undefined, 'pg-actions');
    const add = (label, action, data = {}) => { const b = button(label, () => submit(action, run, data), 'secondary'); b.disabled = busy; actions.append(b); };
    if (run.status === 'ready') { add('Check work', 'check'); add('Stop lab', 'stop'); }
    if (run.status === 'stopped') add('Resume lab', 'resume');
    if (['ready', 'stopped'].includes(run.status)) add('Finish & keep work', 'finish');
    if (run.status !== 'destroyed') add(run.status === 'cleanup_failed' ? 'Retry cleanup' : 'Destroy runtime', 'destroy');
    const exportButton = button('Download saved work', async () => {
      const files = {};
      for (const name of run.files.filter(n => n.startsWith('work/'))) files[name] = (await api(`hosted-labs/runs/${run.id}/files?${new URLSearchParams({name})}`)).content;
      download({run_id: run.id, recipe_id: recipe.id, result: run.result, evidence_label: run.evidence_label, files}, `${recipe.id}-${run.id}.json`);
    }); exportButton.disabled = busy; actions.append(exportButton); root.append(actions);
    if (run.result) {
      const passed = run.result.status === 'pass', finished = Boolean(run.finished_at);
      const result = AscendFeedback.create({kind: passed ? 'success' : 'warning', title: finished ? passed ? 'Lab result saved!' : 'Lab attempt recorded' : passed ? 'Checks passed' : 'Review the failing checks', message: `${recipe.title} · ${run.evidence_label}: ${run.result.status}`}); result.classList.add('hosted-reward-result');
      window.AscendRewards?.decorate(result, {kind: finished && passed ? 'challenge' : 'answer', positive: passed, practice: run.practice_reward, evidence: finished ? 'Your work and its evidence are saved.' : 'Finish & keep work records this attempt and releases the runtime.'});
      if (finished && passed) {
        const next = el('div', undefined, 'pg-actions'); next.append(button('Browse Linux labs', () => playgroundOpen('labs'), '')); window.AscendRewards?.addReplay(result, next); $('.feedback-copy', result).append(next);
      }
      root.append(result);
    }
    if (run.files.length) {
      const fields = el('div'); root.append(fields);
      const file = playgroundField(fields, 'Lab file', selectedFiles.get(run.id) || run.files.find(n => n.startsWith('input/')) || run.files[0], 'text', run.files.map(n => [n, n]));
      const editorLabel = el('label', 'File contents'); editorLabel.htmlFor = 'hosted-file-content';
      const editor = el('textarea'); editor.id = 'hosted-file-content'; editor.spellcheck = false; editor.setAttribute('aria-describedby', 'hosted-file-help');
      const help = el('p', '', 'small muted'); help.id = 'hosted-file-help';
      const save = button('Save file', async () => { await submit('save', run, {name: file.value, content: editor.value}); }); save.disabled = true;
      fields.append(editorLabel, editor, help, save);
      let loaded;
      async function loadFile() {
        const name = file.value; selectedFiles.set(run.id, name); save.disabled = true;
        const data = await api(`hosted-labs/runs/${run.id}/files?${new URLSearchParams({name})}`);
        if (!current() || !fields.isConnected || file.value !== name) return;
        loaded = `${run.id}/${name}`; editor.value = hostedDrafts.get(loaded) ?? data.content; editor.readOnly = !data.editable;
        save.disabled = busy || !data.editable; help.textContent = data.editable ? 'Save your changes before checking. Unsaved edits stay in this tab.' : 'Reference or saved file · read only';
      }
      file.addEventListener('change', () => loadFile().catch(error => notify(error.message, 'error')));
      editor.addEventListener('input', () => { if (loaded) hostedDrafts.set(loaded, editor.value); });
      await loadFile();
    }
    if (run.status !== 'ready') return;
    if (run.targets.length) {
      const draft = hostedConsoleDrafts.get(run.id) || {};
      const request = el('details'); request.open = !!draft.open; request.append(el('summary', 'Send a request to the lab')); const fields = el('div'); request.append(fields);
      const target = playgroundField(fields, 'Lab target', draft.target || run.targets[0], 'text', run.targets.map(t => [t, t]));
      const method = playgroundField(fields, 'HTTP method', draft.method || 'GET', 'text', ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']);
      const path = playgroundField(fields, 'Request path', draft.path || '/', 'text');
      const token = playgroundField(fields, 'Lab bearer token (optional)', draft.token || '', 'password'); token.autocomplete = 'off';
      const bodyLabel = el('label', 'JSON request body (optional)'), body = el('textarea'); body.id = 'hosted-request-body'; bodyLabel.htmlFor = body.id; fields.append(bodyLabel, body);
      body.value = draft.body || '';
      const remember = () => hostedConsoleDrafts.set(run.id, {open: request.open, target: target.value, method: method.value, path: path.value, token: token.value, body: body.value});
      fields.addEventListener('input', remember); request.addEventListener('toggle', remember);
      const send = button('Send lab request', () => { remember(); return submit('http', run, {target: target.value, method: method.value, path: path.value, token: token.value, body: body.value}); }); send.disabled = busy; fields.append(send); root.append(request);
    }
    if (run.router) {
      root.append(el('p', `Router AS: ${run.fixture.router_as}. Peers: ${Object.entries(run.addresses).map(([n, a]) => `${n} ${a}`).join(' · ')}`, 'small'));
      root.append(el('p', 'Configure rtr using FRR commands. The console supports BGP inspection, neighbors, authentication and prefix lists. Use write memory to save and restart the lab’s BGP sessions against the external controls.', 'small'));
      const label = el('label', 'Router commands (one per line)'), input = el('textarea'); input.id = 'hosted-router-commands'; label.htmlFor = input.id; input.value = hostedConsoleDrafts.get(run.id)?.commands || 'show bgp ipv4 unicast summary\nshow bgp ipv4 unicast';
      input.addEventListener('input', () => hostedConsoleDrafts.set(run.id, {commands: input.value}));
      const send = button('Run router commands', () => submit('router', run, {commands: input.value.split('\n').map(c => c.trim()).filter(Boolean)})); send.disabled = busy; root.append(label, input, send);
    }
  }
  async function refresh() {
    clearTimeout(hostedPoll);
    try {
      const data = await api('hosted-labs/runs'); if (!current()) return;
      const signature = JSON.stringify([data.job?.id, data.job?.status, data.runs.map(r => [r.id, r.status, r.result, r.practice_reward?.id, r.practice_reward?.points])]);
      if (signature !== lastSignature) { lastSignature = signature; await draw(data); }
      if (lastJob && data.job?.id === lastJob && data.job.status === 'complete') {
        lastJob = null;
        const run = data.runs.find(r => r.id === data.job.run_id);
        if (['check', 'finish'].includes(data.job.action) && run?.result) {
          if (run.result.status === 'pass') window.AscendRewards?.play(root.querySelector('.hosted-reward-result'), {account, receiptId: `hosted-${data.job.action}:${run.id}`});
          else notify(data.job.action === 'finish' ? 'Attempt saved. Review the checked result.' : 'Check finished. Review the failing conditions.', 'info');
        } else notify('Server lab operation completed.', 'success');
      }
      if (current()) hostedPoll = setTimeout(refresh, data.job && ['queued', 'running'].includes(data.job.status) ? 1500 : 15000);
    } catch (error) {
      if (current()) { root.replaceChildren(el('p', error.message, 'small'), button('Retry server connection', refresh, 'text-button')); lastSignature = null; }
    }
  }
  await refresh();
}
