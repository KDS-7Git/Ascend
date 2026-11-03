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
      if (attempt.result) card.append(el('p', `${attempt.result.evidence_label}: ${attempt.result.status}`), el('p', attempt.result.detail || '', 'small'));
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
  } else root.append(el('p', 'This reference has no integrated exercise yet. Review preparation and upstream instructions before choosing an environment.', 'card'));
  if (state.tab !== 'lab' || state.labRef !== id) return;
  const source = el('details', undefined, 'page-section lab-source'); source.append(el('summary', 'Source, requirements & verification'));
  source.append(el('p', `Preparation: ${lab.prerequisites.join('; ')}`), el('p', lab.delivery), labLink('Upstream repository', lab.repository), el('p', `License: ${lab.license.identifier}`), el('p', `Reviewed source: ${recipe?.source?.revision || lab.reviewed_revision || 'Not yet pinned for execution'}`, 'small'));
  if (recipe?.license_review) source.append(el('p', recipe.license_review, 'small'));
  source.append(el('p', lab.upstream_verification), el('p', `Research notes: ${lab.limits}`, 'small muted'), el('p', 'Levels follow prerequisites and are not calibrated across repositories.', 'small muted')); root.append(source);
}
