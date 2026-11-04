'use strict';

// Standalone design artifact. All accounts, checks, storage, and rewards are sample data.
// No fetch, real authentication, external telemetry, or runtime provisioning is performed.
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeText = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const iconPaths = {
  home:'m3 10 9-7 9 7v10H3V10Zm6 10v-7h6v7',
  compass:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM16 8l-3 5-5 3 3-5 5-3Z',
  layers:'m12 3 10 5-10 5L2 8l10-5ZM3 12l9 5 9-5M3 16l9 5 9-5',
  folder:'M3 6h6l2 3h10v11H3V6Z',
  chart:'M4 20h17M7 16v-5m5 5V5m5 11V8',
  arrow:'M4 12h15m-6-6 6 6-6 6',
  back:'M20 12H5m6-6-6 6 6 6',
  search:'M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0Zm-1 5 6 6',
  spark:'m13 2-8 12h6l-1 8 9-13h-7l1-7Z',
  book:'M12 5C9 3 5 3 2 4v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Zm0 0v15',
  close:'m6 6 12 12M6 18 18 6',
  check:'m5 12 4 4L19 6',
  clock:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 7v6l4 2',
  flag:'M5 22V3m0 1h14l-3 5 3 5H5',
  terminal:'m5 6 5 6-5 6m8 0h6M2 3h20v18H2V3Z',
  server:'M3 3h18v7H3V3Zm0 11h18v7H3v-7Zm4-7h.01M7 18h.01M12 7h5m-5 11h5',
  globe:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 12h18M12 3c-5 5-5 13 0 18 5-5 5-13 0-18Z',
  lock:'M5 11h14v10H5V11Zm3 0V7a4 4 0 0 1 8 0v4m-4 4v3',
  info:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 11v6m0-10v.01',
  filter:'M4 6h16M7 12h10m-7 6h4',
  download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',
  target:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0ZM12 11v2',
  leaf:'M20 3C7 2 2 9 6 16s15 4 14-13ZM5 21l11-12',
  file:'M5 2h9l5 5v15H5V2Zm9 0v6h5M8 12h8m-8 4h6'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${iconPaths[name] || iconPaths.compass}"/></svg>`;
const hydrateIcons = (root = document) => $$('[data-icon]', root).forEach(node => { node.innerHTML = icon(node.dataset.icon); });

function scene(celebrating = false) {
  return `<svg viewBox="0 0 260 240" fill="none" aria-hidden="true">
    <ellipse cx="133" cy="215" rx="99" ry="15" fill="#09261d" opacity=".16"/>
    <path d="m24 199 111-41 106 37-109 37-108-33Z" fill="#49684c"/>
    <path d="m24 193 111-41 106 37-109 37-108-33Z" fill="#a5bc8b"/>
    <path d="m40 193 95-34 90 31-94 31-91-28Z" stroke="#d6dfb9" opacity=".45"/>
    <path d="M85 183h25q13 0 13-13v-8" stroke="#e0d1a9" stroke-width="4" stroke-linecap="round"/>
    <path d="m173 172 21 7v15l-21-7v-15Z" fill="#47695b"/><path d="m173 172 18-7 21 7-18 7-21-7Z" fill="#b0c6b5"/><path d="m194 179 18-7v15l-18 7v-15Z" fill="#748f7b"/>
    <path d="m173 154 21 7v15l-21-7v-15Z" fill="#47695b"/><path d="m173 154 18-7 21 7-18 7-21-7Z" fill="#ccd7bf"/><path d="m194 161 18-7v15l-18 7v-15Z" fill="#91a68c"/>
    <circle class="scene-dot" cx="181" cy="161" r="2" fill="#e6eb9c"/><circle cx="181" cy="179" r="2" fill="#e6eb9c"/>
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
    <g class="companion-eye" fill="#f6f5d7"><ellipse cx="113" cy="106" rx="4" ry="6"/><ellipse cx="137" cy="106" rx="4" ry="6"/></g>
    <path d="${celebrating ? 'm117 115 6 4 7-4' : 'M120 115h8'}" stroke="#d4e1b3" stroke-width="2" stroke-linecap="round"/>
    <rect x="111" y="135" width="27" height="16" rx="5" fill="#e6b95c"/>
    <path d="m119 142 4-4 5 4" stroke="#916e30" stroke-width="1.7" stroke-linecap="round"/>
    <g class="companion-hand"><path d="M160 123q19 9 24-11" stroke="#edc467" stroke-width="9" stroke-linecap="round"/><path d="M184 111V66" stroke="#334b34" stroke-width="3" stroke-linecap="round"/><path d="m185 66 33 4-7 10 5 8-31-3V66Z" fill="${celebrating ? '#e9eba4' : '#c4b4e0'}"/><path d="m193 76 4 4 8-7" stroke="#4f5538" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>
    <path d="m215 209 1-16m-1 9-6-7m7 3 5-9" stroke="#506a42" stroke-width="3" stroke-linecap="round"/>
    ${celebrating ? '<path d="m60 83 3-8m-5 4 8 1m101-43 2-8m-5 4 8 1M202 127l4-5m-5 1 6 4" stroke="#a8b778" stroke-width="2" stroke-linecap="round"/>' : ''}
  </svg>`;
}

const KEY = 'ascend-design-preview-v1';
const initial = () => ({version:1,account:'mira',theme:'light',motion:true,profiles:{
  mira:{name:'Mira',goal:'career',xp:1240,notes:'',exampleNote:'',passed:false,awarded:false,attemptStart:null,attemptEnd:null,exampleComplete:false,tourSeen:false,queue:'idle',offerUntil:null,hostedSaved:false},
  arun:{name:'Arun',goal:'explore',xp:640,notes:'',exampleNote:'',passed:false,awarded:false,attemptStart:null,attemptEnd:null,exampleComplete:false,tourSeen:false,queue:'idle',offerUntil:null,hostedSaved:false}
}});
let model = initial();
let storageAvailable = true;
try { const saved = JSON.parse(localStorage.getItem(KEY)); if (saved?.version === 1 && saved.profiles?.mira && saved.profiles?.arun) model = saved; } catch { storageAvailable = false; }
let currentRoute = '', toastTimer, saveTimer, tourStep = 0, tourVisible = false, catalogFilter = 'all';
const profile = () => model.profiles[model.account];
const persist = () => { try { localStorage.setItem(KEY, JSON.stringify(model)); storageAvailable=true; return true; } catch { storageAvailable=false; return false; } };
const saveHint = hasValue => storageAvailable ? (hasValue ? 'Saved in this preview → My work' : 'Notes save in this preview → My work') : 'Kept in this open tab only. Browser storage failed; download a copy before closing.';
const navItems = [{id:'today',label:'Today',icon:'home'},{id:'playground',label:'Playground',icon:'compass'},{id:'devops',label:'DevOps path',mobile:'DevOps',icon:'layers'},{id:'work',label:'My work',icon:'folder'},{id:'progress',label:'Progress',icon:'chart'}];
const activities = [
  {title:'The release is running. Why the 502?',detail:'Independent challenge · Intermediate · Browser',minutes:'20 min',kind:'challenge',route:'challenge',icon:'terminal',color:'peach'},
  {title:'Follow a request to your application',detail:'Worked example · 3 steps · No setup',minutes:'6 min',kind:'example',route:'example',icon:'book',color:''},
  {title:'Try a deployment behind a secure edge',detail:'Hosted lab preview · Intermediate · Server or local',minutes:'25 min',kind:'lab',route:'queue',icon:'server',color:'green'},
  {title:'From commit to a reliable deployment',detail:'DevOps track · 13 chapters · Local and browser practice',minutes:'Track',kind:'track',route:'devops',icon:'layers',color:''}
];
const chapters = [
  ['Follow a request','Trace browser → DNS → proxy → application.','HTTP · DNS · curl'],
  ['Operate a Linux host','Find the process, inspect logs, and reason about permissions.','Linux · shell · SSH'],
  ['Build a versioned release','Turn a reviewed commit into an identifiable artifact.','Git · dependencies · build metadata'],
  ['Run a reliable service','Run as a dedicated user and recover from a process failure.','systemd · environment configuration'],
  ['Deploy behind a secure edge','Make the service reachable and verify the right boundary.','Reverse proxy · TLS · health checks'],
  ['Package with containers','Build once and preserve application data across restarts.','Docker · Compose · volumes'],
  ['Test every change in CI','Use a pipeline to verify and publish a release.','GitHub Actions · artifact registry'],
  ['Release and roll back','Promote an immutable artifact and restore a known good release.','Deployment strategy · rollback'],
  ['Recreate infrastructure','Plan, review, create, change, and safely destroy a sandbox.','OpenTofu / Terraform · Ansible'],
  ['Observe service health','Find an incident through useful metrics, logs, and alerts.','Prometheus · Grafana · SLOs'],
  ['Protect and recover data','Keep secrets out of artifacts and prove a backup restores.','Secrets · backup · recovery'],
  ['Deploy to Kubernetes','Understand a deployment, service, configuration, and rollout.','Local Kubernetes · kubectl'],
  ['Operate the capstone','Ship Relay v2, handle a regression, recover, and hand it over.','Release evidence · incident record · runbook']
];

function notify(message) { clearTimeout(toastTimer); $('#toast').textContent = message; $('#toast').hidden = false; toastTimer = setTimeout(() => { $('#toast').hidden = true; }, 5500); }
function openDialog(id) { const node = $(id); if (!node.open) node.showModal(); }
function closeDialogs() { $$('dialog[open]').forEach(dialog => dialog.close()); }
function goalText() { return {career:'Preparing for a job',explore:'Following your curiosity',both:'Career + curiosity'}[profile().goal]; }
function activeChallenge() { return profile().attemptStart && !profile().attemptEnd && !profile().passed; }
function activeHosted() { return ['running','checked'].includes(profile().queue); }
function applyPreferences() {
  document.documentElement.dataset.theme = model.theme;
  const systemReduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.documentElement.dataset.motion = model.motion && !systemReduced ? 'on' : 'off';
  $('#theme-toggle').setAttribute('aria-checked', String(model.theme === 'dark'));
  $('#motion-toggle').setAttribute('aria-checked', String(model.motion && !systemReduced));
  $('#motion-toggle').disabled = systemReduced;
  $('#motion-help').textContent = systemReduced ? 'Reduced motion is enabled on your device.' : 'Short, purposeful transitions and reactions.';
}
function updateChrome() {
  const active = ['challenge','example','queue'].includes(currentRoute) ? 'playground' : currentRoute;
  $('#desktop-nav').innerHTML = navItems.map(item => `<a class="nav-link ${active === item.id ? 'active' : ''}" href="#${item.id}" ${active === item.id ? 'aria-current="page"' : ''}>${icon(item.icon)}${item.label}${item.id === 'devops' ? '<span class="nav-badge">NEW</span>' : ''}</a>`).join('');
  $('#mobile-nav').innerHTML = navItems.map(item => `<a class="nav-link ${active === item.id ? 'active' : ''}" href="#${item.id}" ${active === item.id ? 'aria-current="page"' : ''}>${icon(item.icon)}${item.mobile || item.label}</a>`).join('');
  const title = {today:'Today',playground:'Playground',devops:'DevOps path',work:'My work',progress:'Progress',challenge:'Challenge',example:'Worked example',queue:'Hosted lab'}[currentRoute] || 'Today';
  $('#breadcrumb').innerHTML = `${['challenge','example','queue'].includes(currentRoute) ? 'Playground' : 'Your workspace'} <span>/</span> ${title}`;
  $('#xp-total').textContent = profile().xp.toLocaleString();
  $('#avatar').textContent = profile().name[0]; $('#account-name').textContent = profile().name;
  $('#learner-select').value = model.account; $('#goal-select').value = profile().goal;
  document.title = `${title} · Ascend design preview`;
}
function heading(eyebrow, title, subtitle = '', side = '') { return `<header class="page-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1>${subtitle ? `<p class="muted">${subtitle}</p>` : ''}</div>${side}</header>`; }
function activityRow(item) { return `<a class="activity-row" href="#${item.route}"><span class="card-icon ${item.color}">${icon(item.icon)}</span><div class="row-copy"><h3>${item.title}</h3><p>${item.detail}</p></div><span class="row-meta">${item.minutes}</span>${icon('arrow')}</a>`; }
function today() {
  const name = escapeText(profile().name);
  return `<div class="page">${heading(`GOOD TO SEE YOU, ${name.toUpperCase()}`, 'Make something work<br>in the real world.', 'A small challenge. A little more understanding.', '<span class="date-note">Tuesday, 3 November</span>')}
    <div class="dashboard-grid"><div>
      <section class="hero" aria-labelledby="recommendation-title"><div class="hero-copy"><p class="eyebrow">YOUR NEXT STEP · DEVOPS</p><h2 id="recommendation-title">Your app is running.<br>Your users still see 502.</h2><p>Follow a request, find the broken link, and bring Relay back online.</p><div class="hero-meta"><span>${icon('clock')}20 min</span><span>${icon('layers')}Intermediate</span><span>${icon('globe')}In your browser</span></div><div class="hero-actions"><a href="#challenge" class="primary">${profile().passed ? 'Review your solution' : activeChallenge() ? 'Resume investigation' : 'Let’s investigate'} ${icon('arrow')}</a><a href="#example" class="text-link">See a worked example</a></div></div><div class="hero-art">${scene(profile().passed)}</div></section>
      <div class="section-top"><h2>Make room for curiosity.</h2><a href="#playground" class="quiet">Explore Playground ${icon('arrow')}</a></div>
      <div class="two-cards"><a href="#example" class="discovery-card"><div class="card-top"><span class="card-icon">${icon('book')}</span><span class="card-tag">LEARN BY WATCHING</span></div><h3>Follow the request.</h3><p>Watch a request travel from the browser to an application, one step at a time.</p><div class="card-foot"><span>6 min · Worked example</span>${icon('arrow')}</div></a><a href="#queue" class="discovery-card"><div class="card-top"><span class="card-icon peach">${icon('server')}</span><span class="card-tag">GET YOUR HANDS ON IT</span></div><h3>Step into a live lab.</h3><p>See the proposed environment flow, including what happens when both slots are in use.</p><div class="card-foot"><span>Hosted lab · Design preview</span>${icon('arrow')}</div></a></div>
      <div class="section-top"><h2>Your expedition.</h2><a href="#devops" class="quiet">View the path ${icon('arrow')}</a></div>
      <nav class="journey" aria-label="DevOps chapter groups"><a href="#devops" class="journey-stop done"><span class="stop-dot">${icon('check')}</span><strong>Get your bearings</strong><small>Foundations · 3 chapters</small></a><a href="#devops" class="journey-stop current"><span class="stop-dot">${icon('flag')}</span><strong>Build & ship</strong><small>You are here</small></a><a href="#devops" class="journey-stop"><span class="stop-dot">3</span><strong>Observe & recover</strong><small>Reliable operations</small></a><a href="#devops" class="journey-stop"><span class="stop-dot">4</span><strong>Bring it together</strong><small>A real release story</small></a></nav>
    </div><aside class="dashboard-aside"><section class="side-panel"><p class="eyebrow">YOUR DIRECTION</p><h3>${goalText()}</h3><div class="progress-ring"><svg viewBox="0 0 110 110" aria-hidden="true"><circle cx="55" cy="55" r="46"/><circle cx="55" cy="55" r="46"/></svg><strong>5 / 13<small>current chapter</small></strong></div><p>You’re connecting the application to the world outside it.</p><button class="quiet goal-open">Adjust your goal ${icon('arrow')}</button></section>
    <section class="side-panel"><p class="eyebrow">A LITTLE MOMENTUM</p><h3>Keep a rhythm that fits.</h3><div class="week-dots">${['M','T','W','T','F','S','S'].map((day,i) => `<div class="week-day">${day}<span class="${i===0 ? 'done' : i===1 ? 'today' : ''}">${i===0 ? icon('check') : i===1 ? '3' : ''}</span></div>`).join('')}</div><p>Your next useful session matters more than a perfect calendar.</p><a href="#progress" class="quiet">See your progress ${icon('arrow')}</a></section>
    <section class="field-note"><h3>${icon('leaf')}A note for the journey</h3><p>A reliable deployment is one you can explain, repeat, and recover.</p></section></aside></div></div>`;
}
function playground() {
  return `<div class="page">${heading('FOLLOW A QUESTION. FIND SOMETHING NEW.', 'Your practice, your way.', 'Build confidence, take a stretch, or follow your curiosity.', `<button class="goal-chip goal-open">${icon('target')}${goalText()}</button>`)}
    <div class="filter-line"><div class="search-field">${icon('search')}<label class="sr-only" for="catalog-search">Search practice</label><input id="catalog-search" type="search" placeholder="Find a skill, question, or challenge…"></div><button class="secondary" id="experienced-entry">I know the basics ${icon('arrow')}</button></div>
    <div class="chips" role="group" aria-label="Activity type">${[['all','For you'],['challenge','Challenges'],['example','Worked examples'],['lab','Live labs']].map(([id,label]) => `<button class="chip" data-filter="${id}" aria-pressed="${catalogFilter===id}">${label}</button>`).join('')}</div>
    <div class="catalog-feature" id="catalog-feature" ${catalogFilter!=='all'?'hidden':''}><section class="example-panel"><p class="eyebrow">WORKED EXAMPLE · 6 MIN</p><h2>See the idea.<br>Then try it yourself.</h2><p>Follow a request through a small system. Three steps, with room to ask why.</p><a href="#example" class="secondary">Study the example ${icon('arrow')}</a><span class="book-art" aria-hidden="true">${icon('book')}</span></section><section class="challenge-panel"><p class="eyebrow">INDEPENDENT CHALLENGE · 20 MIN</p><h2>A release worth<br>investigating.</h2><p>The application starts, but its users see an error. Find the broken connection and check your repair.</p><a href="#challenge" class="primary">Take the challenge ${icon('arrow')}</a><p style="margin:17px 0 0"><span class="availability">Browser ready · No lab slot needed</span></p></section></div>
    <div class="section-top"><h2 id="catalog-list-title">A few good places to start.</h2><span class="muted" style="font-size:.68rem">Sample activity catalog</span></div><div class="activity-list" id="catalog-list">${activities.map(activityRow).join('')}</div></div>`;
}
function devops() {
  return `<div class="page">${heading('ONE APPLICATION. THE WHOLE JOURNEY.', 'From commit to confidence.', 'Learn how deployments work—and how to recover when they don’t.')}
    <section class="track-hero"><div class="track-hero-art">${scene()}</div><div><p class="eyebrow">DEVOPS FOUNDATIONS · CURRICULUM DESIGN</p><h2>Meet Relay. Build its way to production.</h2><p class="muted">Take one small web service through a repeatable release, useful monitoring, a failed deployment, and a proven recovery.</p><div class="track-meta"><span>13 practical chapters</span><span>Browser + learner-local labs</span><span>Optional hosted slices</span></div></div></section>
    <div class="curriculum"><section aria-labelledby="chapters-title"><div class="section-top" style="margin-top:0"><h2 id="chapters-title">Your route.</h2><span class="tag">Proposed curriculum</span></div>${chapters.map((chapter,i) => `<div class="chapter-row"><span class="chapter-index ${i<4?'done':i===4?'current':''}">${i<4?icon('check'):String(i+1).padStart(2,'0')}</span><div class="chapter-copy"><h3>${chapter[0]}</h3><p>${chapter[1]}</p><div class="chapter-tools">${chapter[2]}</div></div>${i===4?'<a class="quiet" href="#challenge">Preview →</a>':''}</div>`).join('')}</section><aside><section class="side-panel"><p class="eyebrow">WHAT YOU WILL BE ABLE TO DO</p><h3>Ship, explain, recover.</h3><p>Build an identifiable release, make it reachable, observe its health, roll it back, and prove your data survives.</p><p>Keep a deployment record and runbook another person can use.</p></section><section class="side-panel"><p class="eyebrow">ALREADY DOING THIS?</p><h3>Start from your evidence.</h3><p>Use an optional practical check or choose the chapter where your understanding starts to get uncertain.</p><a href="#challenge" class="quiet">Try an intermediate case ${icon('arrow')}</a></section><section class="field-note"><h3>${icon('server')}Choose your environment</h3><p>Use browser cases immediately. Run full build pipelines and clusters on your own sandbox. Hosted slices use the shared two-slot runner.</p></section></aside></div></div>`;
}
function conflict(destination) {
  return `<div class="page">${heading('YOUR CURRENT ATTEMPT', 'Keep the switch deliberate.', 'Your independent challenge is still running. Its original clock continues while you browse.')}<section class="queue-panel"><h2>Study the example?</h2><p class="muted">End the current assessed attempt before opening a teaching activity. Your notes stay saved; ending the attempt does not award completion XP.</p><div class="work-actions"><a href="#challenge" class="primary">Return to your challenge ${icon('arrow')}</a><button class="secondary" data-end-then="${destination}">End attempt and open example</button></div></section></div>`;
}
function hostedConflict(destination) {
  return `<div class="page">${heading('YOUR ACTIVE ENVIRONMENT', 'One active task at a time.', 'Your hosted lab is still running. Browsing does not release it.')}<section class="queue-panel"><h2>Keep your work and make room.</h2><p class="muted">Return to the active lab, or finish it and retain the sample work before opening ${destination==='example'?'a worked example':'an independent challenge'}.</p><div class="work-actions"><a href="#queue" class="primary">Return to the lab ${icon('arrow')}</a><button class="secondary" data-release-then="${destination}">Finish lab &amp; keep work</button></div></section></div>`;
}
function diagram(example = false, repaired = false) {
  return `<div class="service-diagram" aria-label="Browser reaches proxy; ${repaired ? 'edge reaches the private app host' : example ? 'proxy expects 7000 but app listens on 9000' : 'edge points to its own loopback while the app is on a separate private host'}"><div class="service-node">${icon('globe')}Browser</div><div class="service-link">HTTPS<span class="line"></span></div><div class="service-node">${icon('server')}${example?'Proxy':'EDGE-1'}</div><div class="service-link ${repaired?'':'broken'}">${repaired?'200 OK':example?':7000':'loopback'}<span class="line"></span></div><div class="service-node">${icon('terminal')}${example?'App :9000':'APP-1'}</div></div>`;
}
const tourSteps = [
  ['Observe the failed connection','The browser reaches the proxy. Read the upstream error to find where the next connection stops.','example-evidence'],
  ['Compare what each side expects','The proxy calls port 7000. The application says it listens on 9000. A healthy process can still be unreachable through its proxy.','example-config'],
  ['Check the repair and the control','Point the upstream at 9000, then check both the page and the health endpoint. A fresh independent challenge follows with a different fixture.','example-control']
];
function tourMarkup() {
  const [title,copy] = tourSteps[tourStep];
  return `<section class="tour-card" aria-label="Worked example walkthrough"><div class="tour-copy"><p class="tour-counter">STEP ${tourStep+1} OF 3</p><h2>${title}</h2><p>${copy}</p></div><div class="tour-actions"><button class="primary" id="tour-next">${tourStep===2?'Finish walkthrough':tourStep===0?'Compare both sides':'Check the repair'} ${icon('arrow')}</button><button class="quiet" id="tour-skip">Skip tour</button></div></section>`;
}
function example() {
  if (activeHosted()) return hostedConflict('example');
  if (activeChallenge()) return conflict('example');
  return `<div class="page"><div class="workbench-head"><a class="back-link" href="#playground">${icon('back')}Back to Playground</a><span class="tag purple">Worked example · No assessment XP</span></div><div class="workbench-title"><p class="eyebrow">SEE THE REASONING, ONE STEP AT A TIME</p><h1>Follow a request.<br>Find the broken connection.</h1><p>Watch one small deployment fail, compare its configuration, and check a repair. You can skip the tour and read at your own pace.</p></div><div id="tour-slot">${tourVisible ? tourMarkup() : '<button class="quiet" id="tour-restart">Show the three-step walkthrough →</button>'}</div>
    <div class="work-grid"><section class="workspace-panel"><div class="workspace-tabs"><span>Demonstration</span><span class="file-label">Fixture A · Example</span></div><div class="evidence-body"><div id="example-evidence"><h2>1. Observe the request.</h2>${diagram(true)}<pre class="code-block"><span class="comment"># Proxy log</span>\n<span class="warn">GET / → 502 Bad Gateway</span>\nupstream: http://127.0.0.1:7000\nconnect() failed: connection refused</pre></div><div id="example-config"><h2>2. Compare both sides.</h2><pre class="code-block"><span class="comment"># Proxy and app run on this same example host</span>\nProxy upstream: 127.0.0.1:7000\n\n<span class="comment"># Application startup</span>\nRelay is listening on 127.0.0.1:9000\nGET /health → 200 OK</pre><p class="muted" style="font-size:.78rem">The app is healthy on port 9000. The proxy points at 7000. Restarting the browser will not change that mismatch.</p></div><div id="example-control"><h2>3. Repair, then check.</h2><pre class="code-block"><span class="comment"># Correct upstream, then verify</span>\nproxy_pass http://127.0.0.1:9000;\nGET /        → 200 OK\nGET /health → 200 OK</pre><p class="muted" style="font-size:.78rem">The result checks both the user-facing page and the health endpoint. It establishes this routing repair, not every property of the deployment.</p></div></div></section>
    <aside><section class="note-panel"><h2>Keep the idea.</h2><p>What would you compare first next time?</p><div class="note-entry"><label for="example-note">Your learning note</label><textarea id="example-note" placeholder="I would compare…">${escapeText(profile().exampleNote)}</textarea><div class="save-status" id="save-status">${saveHint(!!profile().exampleNote)}</div></div><div class="finish-line"><h3>What this example teaches</h3><ul><li>A process can be healthy while routing is broken.</li><li>Compare the expected and actual connection.</li><li>Check the repair against a useful control.</li></ul></div><div class="work-actions"><button class="primary" id="complete-example">${profile().exampleComplete?'Example recorded':'Finish the example'}</button></div></section><p class="work-help">The independent challenge uses another fixture and keeps its own result.</p></aside></div></div>`;
}
function challenge() {
  if (activeHosted()) return hostedConflict('challenge');
  const p = profile();
  return `<div class="page"><div class="workbench-head"><a class="back-link" href="#playground">${icon('back')}Back to Playground</a><div class="timer">${icon('clock')}<strong id="attempt-timer">${p.attemptStart?'00:00':'Not started'}</strong><span>${p.passed ? 'Complete' : p.attemptEnd ? 'Attempt ended' : p.attemptStart ? 'Original clock continues' : '20 min estimate'}</span></div></div><div class="workbench-title"><p class="eyebrow">INDEPENDENT CHALLENGE · DEVOPS</p><h1>The release is running.<br>Why are users seeing 502?</h1><p>Inspect evidence from the edge host and the app host. Restore the page, keep the health check working, and keep direct public access to the app blocked.</p></div><div class="work-meta"><span class="tag orange">Intermediate</span><span>Browser exercise · No hosted slot</span><span>Fixture B · ${p.passed?'Familiar review':'Independent case'}</span><span>${p.passed?'First-solve reward recorded':'50 XP on first successful completion'}</span></div>
    ${!p.attemptStart ? `<section class="tour-card"><div class="tour-copy"><h2>Ready to investigate?</h2><p>Your task is to select a repair and check its result. Once started, this attempt’s clock continues when you leave. Your notes stay available in My work.</p></div><div class="tour-actions"><button class="primary" id="begin-attempt">Start challenge ${icon('arrow')}</button></div></section>` : ''}
    <div class="work-grid"><section class="workspace-panel"><div class="workspace-tabs"><span>Deployment evidence</span><span class="file-label">Relay · v1.2</span></div><div class="evidence-body"><h2>Trace the failing request.</h2>${diagram(false,p.passed)}<div class="file-heading"><span>${icon('file')}edge.log</span><span>Observed after release</span></div><pre class="code-block"><span class="comment"># EDGE-1 · user-facing request</span>\n<span class="warn">GET / → 502 Bad Gateway</span>\nupstream: http://127.0.0.1:8080\nconnect() failed: connection refused\n\n<span class="comment"># EDGE-1 · probe to the private app host</span>\nGET http://10.20.0.8:8000/health → 200 OK</pre><div class="file-heading"><span>${icon('file')}application.log</span><span>Same release</span></div><pre class="code-block"><span class="comment"># APP-1 · private address 10.20.0.8</span>\nRelay v1.2 listening on 10.20.0.8:8000\nGET /health → 200 OK\n\n<span class="comment"># Access policy</span>\nEDGE-1 → APP-1:8000 allowed\nPublic internet → APP-1:8000 blocked</pre></div>
    <form id="repair-form" class="repair-form"><fieldset ${!p.attemptStart || p.attemptEnd || p.passed ? 'disabled' : ''}><legend>Which repair is supported by this evidence?</legend><label class="radio-row"><input type="radio" name="repair" value="restart" required><span>Keep the upstream on 127.0.0.1, but change its port to 8000.</span></label><label class="radio-row"><input type="radio" name="repair" value="port" required ${p.passed?'checked':''}><span>Use the app’s private address, 10.20.0.8:8000, and preserve its access policy.</span></label><label class="radio-row"><input type="radio" name="repair" value="health" required><span>Expose APP-1:8000 to the public internet and bypass the edge.</span></label></fieldset><div id="repair-result" ${p.passed?'':'hidden'}>${p.passed?successReceipt(false):''}</div><div class="work-actions"><button class="primary" id="check-repair" ${!p.attemptStart || p.attemptEnd || p.passed?'disabled':''}>${p.passed?'Result recorded':'Check my repair'} ${icon('check')}</button><a href="#work" class="quiet">Save & leave</a></div>${p.attemptEnd&&!p.passed?'<p class="fine-print">This attempt was explicitly ended. Your work is retained. Use Reset sample progress in the design controls to try a new preview.</p>':''}</form></section>
    <aside><section class="note-panel"><h2>Your field notes</h2><p>Keep a hypothesis and the observation that supports it.</p><div class="note-entry"><label for="work-note">Notes and evidence</label><textarea id="work-note" placeholder="My hypothesis is…\nThe evidence I’m using is…">${escapeText(p.notes)}</textarea><div class="save-status" id="save-status">${saveHint(!!p.notes)}</div></div><div class="finish-line"><h3>You are done when</h3><ul><li>Your repair restores the page.</li><li>The health endpoint still responds.</li><li>Direct public access to the app remains blocked.</li></ul></div><a href="#work" class="quiet">Open My work ${icon('arrow')}</a></section><details class="work-help"><summary>Need to revisit the idea?</summary><p>Study the separate worked example. Opening it requires ending any running scored attempt first.</p><a class="text-link" href="#example">Open the example</a></details><p class="fine-print">Design simulation: these checks run on sample data in your browser. Production assessment requires server-authoritative evidence.</p></aside></div></div>`;
}
function successReceipt(animate = true) {
  return `<section class="result-box success" ${animate?'':'style="animation:none"'} aria-labelledby="result-title"><h3 id="result-title">${icon('check')}The connection is restored.</h3><p>The proxy reaches the application over its private address. The health check works and direct public access remains blocked.</p><ul class="receipt-list"><li>Page request: 200 OK</li><li>Health endpoint: 200 OK</li><li>Direct public app access: blocked</li><li>First successful completion: 50 challenge XP</li></ul><div class="result-actions"><a href="#work" class="secondary">View saved result ${icon('arrow')}</a><a href="#devops" class="text-link">Next: package a repeatable release</a></div><p class="fine-print">Sample result. Reopening or rechecking does not award this XP again.</p></section>`;
}
function queue() {
  const q=profile().queue;
  const step = {idle:0,queued:0,offered:1,running:2,checked:2,released:3,expired:0}[q] || 0;
  const copy = {
    idle:'<strong>Both hosted slots are in use.</strong> Keep this lab in your queue or choose a browser exercise while you wait.',
    queued:'<strong>You are first in the sample queue.</strong> No runtime has started. You can keep learning in the browser; the offer will appear here when a slot is available.',
    offered:'<strong>A slot is ready for you.</strong> Claim it within <span id="offer-timer">90</span> seconds. Joining the queue alone never starts a lab.',
    running:'<strong>Your simulated lab is running.</strong> Check the service, then finish and keep its result to release the runtime.',
    checked:'<strong>The simulated runtime check passed.</strong> The page and health endpoint respond. This records observed controls; hosted checks earn no XP.',
    released:'<strong>Work retained. Runtime released.</strong> The sample result is in My work. The slot can now serve the next learner.',
    expired:'<strong>The offer expired.</strong> No runtime was started and your work is safe. Rejoin when you are ready.'
  }[q];
  let actions='';
  if(['idle','expired'].includes(q)) actions='<button class="primary" id="join-queue">Join the lab queue '+icon('arrow')+'</button><a class="secondary" href="#challenge">Try the browser case</a>';
  if(q==='queued') actions='<button class="secondary" id="cancel-queue">Leave the queue</button><a class="text-link" href="#playground">Keep exploring '+icon('arrow')+'</a>';
  if(q==='offered') actions=`<button class="primary" id="claim-lab">${activeChallenge()?'Finish current challenge to claim':'Start the lab'} ${icon('arrow')}</button><button class="secondary" id="cancel-queue">Not now</button>`;
  if(['running','checked'].includes(q)) actions=`<button class="primary" id="check-hosted">${q==='checked'?'Check again':'Check the service'} ${icon('check')}</button><button class="secondary" id="finish-hosted">Finish & keep work</button>`;
  if(q==='released') actions='<a class="primary" href="#work">Open saved work '+icon('arrow')+'</a><a class="text-link" href="#playground">Choose another activity</a>';
  return `<div class="page"><a class="back-link" href="#playground">${icon('back')}Back to Playground</a>${heading('LIVE PRACTICE · HOSTED LAB PREVIEW','A place to try it for real.','Learn the environment flow without losing your place.')}<section class="queue-panel"><div class="queue-title"><span class="card-icon green">${icon('server')}</span><div><h2>Relay behind a secure edge</h2><p>Inspect routing, test reachability, and retain the useful evidence when the runtime closes.</p><span class="tag">Two hosted slots · One active lab per learner</span></div></div><div class="queue-steps">${['Waiting','Ready to start','Working','Released'].map((name,i)=>`<div class="queue-step ${step===i?'active':''}"><span>${step>i?'✓':i+1}</span>${name}</div>`).join('')}</div><p class="queue-copy">${copy}</p><div class="work-actions">${actions}</div>${q==='offered'&&activeChallenge()?'<p class="fine-print">Your independent challenge is still running. Finish or explicitly end it before claiming another active task.</p>':''}<div class="demo-control"><strong>DESIGN REVIEW CONTROL</strong><br>${q==='queued'?'<button class="quiet" id="offer-slot">Simulate a slot becoming free →</button>':'Queue and runtime events are simulated. No container is launched.'}</div></section><div class="section-top"><h2>Useful work while you wait.</h2></div><div class="two-cards"><a href="#challenge" class="discovery-card"><div class="card-top"><span class="card-icon peach">${icon('terminal')}</span><span class="card-tag">SAME DIFFICULTY, SMALLER ENVIRONMENT</span></div><h3>Investigate the deployment evidence.</h3><p>An intermediate browser case that needs no hosted slot.</p><div class="card-foot"><span>20 min · Independent challenge</span>${icon('arrow')}</div></a><a href="#devops" class="discovery-card"><div class="card-top"><span class="card-icon">${icon('layers')}</span><span class="card-tag">YOUR OWN TOOLS</span></div><h3>Plan a learner-local deployment.</h3><p>See where the track uses your own toolchain and sandbox.</p><div class="card-foot"><span>DevOps curriculum preview</span>${icon('arrow')}</div></a></div></div>`;
}
function work() {
  const p=profile(),cards=[];
  if(p.attemptStart || p.notes || p.passed) cards.push(`<article class="saved-card"><header><div><p class="eyebrow">INDEPENDENT CHALLENGE · RELAY</p><h2>The release is running. Why the 502?</h2></div><span class="tag ${p.passed?'green':''}">${p.passed?'Passed':p.attemptEnd?'Ended':'In progress'}</span></header><p>${escapeText(p.notes || 'No note yet. The attempt and its current result are retained.')}</p>${p.passed?'<p>Observed sample controls: page 200 OK; health endpoint 200 OK; direct public app access blocked. First-solve reward recorded: 50 challenge XP.</p>':''}<footer><a class="primary" href="#challenge">${p.passed?'Review result':'Return to the work'} ${icon('arrow')}</a><button class="quiet" data-download="challenge">${icon('download')}Download a copy</button></footer></article>`);
  if(p.exampleNote || p.exampleComplete) cards.push(`<article class="saved-card"><header><div><p class="eyebrow">WORKED EXAMPLE</p><h2>Follow a request to your application</h2></div><span class="tag purple">${p.exampleComplete?'Studied':'Note saved'}</span></header><p>${escapeText(p.exampleNote || 'You studied the routing example. Try the separate independent case when you are ready.')}</p><footer><a class="secondary" href="#example">Revisit example ${icon('arrow')}</a><button class="quiet" data-download="example">${icon('download')}Download a copy</button></footer></article>`);
  if(p.hostedSaved) cards.push(`<article class="saved-card"><header><div><p class="eyebrow">HOSTED LAB SIMULATION</p><h2>Relay behind a secure edge</h2></div><span class="tag green">Runtime released</span></header><p>Sample runtime observations retained. This is a hosted-control receipt, not independent skill verification. No XP was awarded.</p><footer><a class="secondary" href="#queue">View environment result ${icon('arrow')}</a></footer></article>`);
  return `<div class="page">${heading('YOUR NOTES, ATTEMPTS, AND RESULTS','Pick up the thread.',`Saved work for ${escapeText(p.name)}. A download makes a separate copy on your device.`)}${cards.length?cards.join(''):`<section class="empty-state"><span class="card-icon" style="margin:0 auto 18px">${icon('folder')}</span><h2>Your next discovery belongs here.</h2><p>Start an activity or write a learning note. Its work and result will stay together, ready for your next session.</p><a href="#playground" class="primary">Find something to explore ${icon('arrow')}</a></section>`}<p class="fine-print">${storageAvailable ? 'In this standalone preview, sample work is saved in this browser.' : 'Browser storage failed. This work is held only in the open tab; download a copy before closing.'} The production design will confirm server persistence separately from a device download.</p></div>`;
}
function progress() {
  const p=profile();
  return `<div class="page">${heading('UNDERSTANDING YOU CAN BUILD ON','See what is getting stronger.','Habit, activity rewards, and skill evidence tell different parts of your story.')}<div class="progress-grid"><section class="metric-card"><p class="eyebrow">ACTIVITY REWARDS</p><strong>${p.xp.toLocaleString()} XP</strong><p>Sample total. XP recognises eligible work; it is not a measure of job readiness.</p></section><section class="metric-card"><p class="eyebrow">PRACTICE RHYTHM</p><strong>1 useful day</strong><p>A meaningful session counts. Return when your schedule allows.</p></section><section class="metric-card"><p class="eyebrow">THIS PREVIEW</p><strong>${p.passed?'1':'0'} fresh solve${p.passed?'':'s'}</strong><p>${p.passed?'One successful routing case. Transfer to another case remains to be demonstrated.':'Start a case to see how a specific result becomes useful evidence.'}</p></section></div><div class="section-top"><h2>Your skill evidence.</h2><span class="tag">Sample learner history</span></div><div class="skills-list"><div class="skill-row"><div><strong>Reading a request path</strong><p>Two earlier sample cases, including a changed condition.</p></div><span class="tag green">Demonstrated</span></div><div class="skill-row"><div><strong>Diagnosing an upstream mismatch</strong><p>${p.passed?'One fresh successful case; try a transfer next.':'Ready for an independent application.'}</p></div><span class="tag purple">${p.passed?'Developing':'Introduced'}</span></div><div class="skill-row"><div><strong>Recovering a deployment</strong><p>This has not been sampled yet.</p></div><span class="tag">Not assessed</span></div></div><div class="section-top"><h2>A meaningful milestone.</h2></div><section class="field-note"><h3>${icon('flag')}A release you can rely on</h3><p>A chapter celebration can mark a real capability with an explanation of the evidence and a useful next step. <button class="quiet milestone-open">Preview the moment →</button></p></section></div>`;
}

function render(focus = true) {
  const next=location.hash.slice(1).split('?')[0] || 'today';
  currentRoute=['today','playground','devops','challenge','example','queue','work','progress'].includes(next)?next:'today';
  if(currentRoute==='example' && !profile().tourSeen && !activeChallenge() && !activeHosted()){tourVisible=true;tourStep=0;profile().tourSeen=true;persist();}
  const views={today,playground,devops,challenge,example,queue,work,progress};
  $('#main').innerHTML=views[currentRoute]();
  if(!focus && $('#main .page')) $('#main .page').style.animation='none';
  if(currentRoute==='challenge' && !profile().attemptStart && $('#main .work-grid')) $('#main .work-grid').hidden=true;
  if(currentRoute==='playground') { const feature=$('#catalog-feature'); if(feature) feature.prepend($('.challenge-panel',feature)); }
  updateChrome();hydrateIcons($('#main'));bindPage();
  if(currentRoute==='playground') filterCatalog();
  if(focus){$('#main').focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}
  updateTimer();
}
function filterCatalog() {
  const query=($('#catalog-search')?.value || '').toLowerCase();
  const items=activities.filter(item=>(catalogFilter==='all'||item.kind===catalogFilter) && `${item.title} ${item.detail}`.toLowerCase().includes(query));
  $('#catalog-list').innerHTML=items.length?items.map(activityRow).join(''):'<p class="empty-search" style="padding:20px">No sample activity matches. Try another term or activity type.</p>';
  $('#catalog-feature').hidden=catalogFilter!=='all'||!!query;
  $$('.chip').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.filter===catalogFilter)));
}
function queueSave(field, input) {
  const accountId=model.account;
  profile()[field]=input.value;
  const status=$('#save-status');if(status){status.textContent='Saving in this preview…';status.classList.remove('saved');}
  clearTimeout(saveTimer);saveTimer=setTimeout(()=>{const saved=persist();if(model.account===accountId){const current=$('#save-status');if(current){current.textContent=saveHint(true);current.classList.toggle('saved',saved);}}},450);
}
function updateTour() {
  if(!$('#tour-slot')) return;
  $('#tour-slot').innerHTML=tourVisible?tourMarkup():'<button class="quiet" id="tour-restart">Show the three-step walkthrough →</button>';
  $$('.tour-highlight').forEach(node=>node.classList.remove('tour-highlight'));
  for(const [, ,id] of tourSteps){const panel=$(`#${id}`);if(panel)panel.hidden=tourVisible&&id!==tourSteps[tourStep][2];}
  if(tourVisible){$(`#${tourSteps[tourStep][2]}`)?.classList.add('tour-highlight');$('#tour-announcement').textContent=`Step ${tourStep+1} of 3. ${tourSteps[tourStep][0]}`;}else{$('#tour-announcement').textContent='Walkthrough closed. All example steps are available to read.';}
  bindTour();
}
function bindTour() {
  $('#tour-next')?.addEventListener('click',()=>{if(tourStep<2){tourStep++;}else{tourVisible=false;profile().tourSeen=true;persist();}updateTour();(tourVisible?$('#tour-next'):$('#tour-restart'))?.focus({preventScroll:true});});
  $('#tour-skip')?.addEventListener('click',()=>{tourVisible=false;profile().tourSeen=true;persist();updateTour();$('#tour-restart')?.focus();});
  $('#tour-restart')?.addEventListener('click',()=>{tourVisible=true;tourStep=0;updateTour();$('#tour-next')?.focus({preventScroll:true});});
}
function downloadWork(kind) {
  const p=profile();
  const value=`Ascend design preview — sample work\nLearner: ${p.name}\nActivity: ${kind==='example'?'Follow a request':'Relay deployment investigation'}\n\n${kind==='example'?p.exampleNote:p.notes}\n\nResult: ${kind==='example'?(p.exampleComplete?'Example studied':'Notes only'):(p.passed?'Sample controls passed; 50 challenge XP recorded':p.attemptEnd?'Attempt ended':'Work in progress')}\n\nThis file is a design simulation, not an Ascend verification receipt.\n`;
  const url=URL.createObjectURL(new Blob([value],{type:'text/plain;charset=utf-8'}));
  const anchor=document.createElement('a');anchor.href=url;anchor.download=`ascend-preview-${kind}-notes.txt`;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('A copy was downloaded. The sample work also remains in My work.');
}
function bindPage() {
  $$('.goal-open').forEach(button=>button.addEventListener('click',()=>openDialog('#account-dialog')));
  $$('.milestone-open').forEach(button=>button.addEventListener('click',showMilestone));
  $$('.chip').forEach(button=>button.addEventListener('click',()=>{catalogFilter=button.dataset.filter;filterCatalog();}));
  $('#catalog-search')?.addEventListener('input',filterCatalog);
  $('#experienced-entry')?.addEventListener('click',()=>{catalogFilter='challenge';filterCatalog();notify('Independent intermediate practice is available directly. No beginner prerequisite is required in this preview.');});
  $('#begin-attempt')?.addEventListener('click',()=>{if(activeHosted()){render(false);return;}profile().attemptStart=Date.now();profile().attemptEnd=null;persist();render(false);$('#repair-form input')?.focus({preventScroll:true});notify('Challenge started. Your original clock continues when you leave.');});
  $('#work-note')?.addEventListener('input',event=>queueSave('notes',event.target));
  $('#example-note')?.addEventListener('input',event=>queueSave('exampleNote',event.target));
  $('#repair-form')?.addEventListener('submit',event=>{
    event.preventDefault();const p=profile();if(!p.attemptStart||p.attemptEnd||p.passed)return;
    const answer=new FormData(event.currentTarget).get('repair');if(!answer)return;
    const result=$('#repair-result');result.hidden=false;
    if(answer!=='port'){result.innerHTML=`<section class="result-box" role="status"><h3>${icon('info')}One connection still needs attention.</h3><p>${answer==='restart'?'The page still returns 502. The direct probe from EDGE-1 to the private app address still returns 200. Compare the destinations of those two requests.':'Direct public access to APP-1 is now allowed. The task requires that boundary to remain closed while traffic goes through the edge.'}</p></section>`;return;}
    p.passed=true;p.attemptEnd=Date.now();if(!p.awarded){p.xp+=50;p.awarded=true;}persist();
    render(false);const receipt=$('#repair-result .success');receipt.removeAttribute('style');receipt.setAttribute('tabindex','-1');receipt.focus({preventScroll:true});notify('Repair checked. The sample result and 50 challenge XP are recorded once.');
  });
  $('#complete-example')?.addEventListener('click',()=>{profile().exampleComplete=true;profile().tourSeen=true;tourVisible=false;persist();notify('Example recorded. Try a fresh independent case next.');location.hash='work';});
  $$('[data-end-then]').forEach(button=>button.addEventListener('click',()=>{profile().attemptEnd=Date.now();persist();render(false);}));
  $$('[data-release-then]').forEach(button=>button.addEventListener('click',()=>{profile().hostedSaved=true;profile().queue='released';persist();render(false);notify('Sample work retained and lab released before opening another task.');}));
  if(currentRoute==='example'&&!activeChallenge()&&!activeHosted())updateTour();
  $('#join-queue')?.addEventListener('click',()=>{profile().queue='queued';persist();render(false);notify('You joined the sample queue. No runtime has started.');});
  $('#cancel-queue')?.addEventListener('click',()=>{profile().queue='idle';profile().offerUntil=null;persist();render(false);notify('Queue reservation released. Your saved work is unaffected.');});
  $('#offer-slot')?.addEventListener('click',()=>{profile().queue='offered';profile().offerUntil=Date.now()+90000;persist();render(false);notify('A sample slot is ready. Claim it here within 90 seconds.');});
  $('#claim-lab')?.addEventListener('click',()=>{if(activeChallenge()){notify('Finish or explicitly end the current challenge before starting another active task.');location.hash='challenge';return;}if(profile().queue!=='offered'||profile().offerUntil<=Date.now())return;profile().queue='running';profile().offerUntil=null;persist();render(false);notify('The simulated lab is ready. No real runtime was provisioned.');});
  $('#check-hosted')?.addEventListener('click',()=>{profile().queue='checked';persist();render(false);notify('Sample runtime controls passed. Hosted lab checks award no XP.');});
  $('#finish-hosted')?.addEventListener('click',()=>{profile().hostedSaved=true;profile().queue='released';persist();render(false);notify('Sample work retained and runtime released.');});
  $$('[data-download]').forEach(button=>button.addEventListener('click',()=>downloadWork(button.dataset.download)));
}
function updateTimer() {
  const p=profile(),node=$('#attempt-timer');
  if(node&&p.attemptStart){const seconds=Math.max(0,Math.floor(((p.attemptEnd||Date.now())-p.attemptStart)/1000));node.textContent=`${Math.floor(seconds/60).toString().padStart(2,'0')}:${(seconds%60).toString().padStart(2,'0')}`;}
  let expiredCurrent=false;
  for(const [id,item] of Object.entries(model.profiles)){if(item.queue==='offered'&&item.offerUntil<=Date.now()){item.queue='expired';item.offerUntil=null;persist();if(id===model.account)expiredCurrent=true;}}
  if(expiredCurrent&&currentRoute==='queue'){render(false);notify('The sample offer expired. You can rejoin when ready.');}
  const offer=$('#offer-timer');if(offer&&p.offerUntil)offer.textContent=Math.max(0,Math.ceil((p.offerUntil-Date.now())/1000));
}
function showMilestone(){closeDialogs();$('#milestone-art').innerHTML=scene(true);openDialog('#milestone-dialog');}
function renderSearch(){const query=$('#activity-search').value.toLowerCase();const found=activities.filter(item=>`${item.title} ${item.detail}`.toLowerCase().includes(query));$('#search-results').innerHTML=found.length?found.map(item=>`<a href="#${item.route}"><span>${item.title}</span>${icon('arrow')}</a>`).join(''):'<p class="empty-search">No sample activity matches. Try “request” or “DevOps”.</p>';$$('#search-results a').forEach(a=>a.addEventListener('click',closeDialogs));}

hydrateIcons();applyPreferences();render(false);
window.addEventListener('hashchange',()=>{persist();render();});
window.addEventListener('beforeunload',persist);
setInterval(updateTimer,1000);
$('#account-button').addEventListener('click',()=>{updateChrome();openDialog('#account-dialog');});
$('#review-button').addEventListener('click',()=>openDialog('#review-dialog'));
$$('.help-open').forEach(button=>button.addEventListener('click',()=>openDialog('#review-dialog')));
$$('.close-dialog').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
$('#theme-toggle').addEventListener('click',()=>{model.theme=model.theme==='dark'?'light':'dark';applyPreferences();persist();});
$('#motion-toggle').addEventListener('click',()=>{model.motion=!model.motion;applyPreferences();persist();});
matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change',applyPreferences);
$('#goal-select').addEventListener('change',event=>{profile().goal=event.target.value;persist();render(false);notify('Goal updated. The same work and skill evidence remain available.');});
$('#learner-select').addEventListener('change',event=>{clearTimeout(saveTimer);persist();model.account=event.target.value;tourVisible=false;tourStep=0;persist();render(false);notify(`Viewing ${profile().name}’s separate sample workspace.`);});
$('#search-button').addEventListener('click',()=>{renderSearch();openDialog('#search-dialog');$('#activity-search').focus();});
$('#activity-search').addEventListener('input',renderSearch);
document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();renderSearch();openDialog('#search-dialog');$('#activity-search').focus();}});
$('#xp-button').addEventListener('click',()=>{location.hash='progress';});
$('#preview-example').addEventListener('click',()=>{closeDialogs();location.hash='example';});
$('#preview-queue').addEventListener('click',()=>{closeDialogs();location.hash='queue';});
$('#preview-milestone').addEventListener('click',showMilestone);
$('#milestone-next').addEventListener('click',()=>{closeDialogs();location.hash='devops';});
$('#reset-preview').addEventListener('click',()=>{clearTimeout(saveTimer);model=initial();tourVisible=false;tourStep=0;catalogFilter='all';persist();applyPreferences();closeDialogs();location.hash='today';render(false);notify('Sample data reset. No real Ascend data was changed.');});

$('.skip-link').addEventListener('click',event=>{event.preventDefault();$('#main').focus({preventScroll:true});$('#main').scrollIntoView({block:'start',behavior:'instant'});});
