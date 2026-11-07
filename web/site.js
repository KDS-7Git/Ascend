"use strict";
window.AscendSite = (() => {
  const paths = {
    arrow:['M4 12h16m-6-6 6 6-6 6'],
    menu:['M4 6h16M4 12h16M4 18h16'],
    route:['M7 5a2 2 0 1 0 0 .1M17 17a2 2 0 1 0 0 .1','M9 5h6a4 4 0 0 1 0 8H9a4 4 0 0 0 0 8h6'],
    spark:['m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z'],
    sun:['M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8','M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5'],
    moon:['M20.5 13A8.5 8.5 0 0 1 11 3.5 8.5 8.5 0 1 0 20.5 13Z'],
    bolt:['m13 2-9 12h7l-1 8 10-12h-7l1-8Z'],
    check:['m5 12 4 4L19 6'],
    shield:['m12 3 8 3v6c0 4-4 7-8 9-4-2-8-5-8-9V6l8-3Z','m8 12 3 3 5-6'],
    terminal:['M4 4h16a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z','m7 8 4 4-4 4m7 0h3'],
    server:['M4 3h16v7H4V3Zm0 11h16v7H4v-7Z','M7 6h.01M7 17h.01M11 6h6m-6 11h6'],
    book:['M12 5v15M12 5C8 2 4 3 2 4v15c3-1 6-1 10 1 4-2 7-2 10-1V4c-2-1-6-2-10 1Z'],
    flag:['M5 21V3m0 0h14l-3 4 3 4H5'],
    sprout:['M12 21v-9m0 4c-6 0-8-4-8-9 6 0 8 3 8 9Zm0-4c0-6 4-9 9-9 0 6-3 9-9 9Z'],
    search:['M10.5 3a7.5 7.5 0 1 0 0 15 7.5 7.5 0 0 0 0-15Zm5.5 13 5 5'],
    eye:['M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z','M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6'],
    copy:['M8 8h12v13H8V8Z','M16 8V3H3v13h5'],
    download:['M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5'],
    logout:['M9 4H4v16h5','M10 12h11m-4-4 4 4-4 4']
  };
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const icon = name => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '1.7'); svg.setAttribute('stroke-linecap', 'round'); svg.setAttribute('stroke-linejoin', 'round');
    svg.setAttribute('aria-hidden', 'true'); svg.classList.add('site-icon');
    for (const d of paths[name] || paths.spark) { const path = document.createElementNS(svg.namespaceURI, 'path'); path.setAttribute('d', d); svg.append(path); }
    return svg;
  };
  const fillIcons = (root = document) => {
    root.querySelectorAll('[data-site-icon]').forEach(node => {
      const name = node.dataset.siteIcon === 'theme' ? (document.documentElement.dataset.workspaceTheme === 'dark' ? 'sun' : 'moon') : node.dataset.siteIcon;
      node.replaceChildren(icon(name));
    });
  };
  const request = async (path, body, method = 'POST', headers = {}) => {
    const options = {cache:'no-store', headers:{...headers}, signal:AbortSignal.timeout(15000)};
    if (body !== undefined) { options.method = method; options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
    let response;
    try { response = await fetch('/api/' + path, options); }
    catch { throw new Error('The server is not responding. Check your connection and try again.'); }
    let data;
    try { data = await response.json(); } catch { throw new Error('The server returned an unexpected response. Reload and try again.'); }
    if (!response.ok) {
      const error = new Error(typeof data.detail === 'string' ? data.detail : 'Please check the form fields and try again.');
      error.status = response.status;
      if (response.status === 404 && path === 'site' && data.detail === 'Not Found') error.message = 'The running Ascend server needs to load this update. Restart the server, then reload this page.';
      throw error;
    }
    return data;
  };
  let sitePromise;
  const siteOptions = () => sitePromise ||= request('site').catch(error => { sitePromise = null; throw error; });
  const download = (filename, content) => {
    const url = URL.createObjectURL(new Blob([content], {type:'text/plain;charset=utf-8'}));
    const link = element('a'); link.href = url; link.download = filename;
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const empty = (heading, description, action, href) => {
    const panel = element('div', undefined, 'site-empty'); panel.append(icon('search'), element('h2', heading), element('p', description));
    if (action) { const link = element('a', action, 'site-button secondary'); link.href = href; panel.append(link); }
    return panel;
  };
  const categoryIcon = category => ({DevOps:'terminal',Infrastructure:'server',Projects:'sprout',Foundations:'book'}[category] || 'shield');
  const trackCard = track => {
    const card = element('article', undefined, 'site-track-card');
    const top = element('div', undefined, 'site-track-card-top'), mark = element('span', undefined, 'site-track-mark'); mark.append(icon(categoryIcon(track.category)));
    top.append(mark, element('span', track.category, 'site-track-category'));
    const title = element('h3'), link = element('a', track.title); link.href = '/tracks/' + track.id; title.append(link);
    card.append(top, title, element('p', track.description || 'A practical track with a clear next step and a finish line you can demonstrate.', 'site-track-description'));
    const meta = element('div', undefined, 'site-track-meta');
    meta.append(element('span', `${track.main_levels} ${track.main_levels === 1 ? 'level' : 'levels'}`), element('span', `${track.nodes} tasks`), element('span', track.reviewed ? 'Reviewed' : 'Draft curriculum'));
    const explore = element('a', 'Explore track', 'site-text-link'); explore.href = link.href; explore.setAttribute('aria-label', `Explore ${track.title}`); explore.append(icon('arrow'));
    card.append(meta, explore); return card;
  };
  window.AscendArt?.mountBackdrop();
  document.querySelectorAll('[data-companion]').forEach(node => { node.innerHTML = window.AscendArt.companionMarkup(); });
  fillIcons(); window.AscendTheme?.sync();
  new MutationObserver(() => document.querySelectorAll('[data-site-icon="theme"]').forEach(node => { node.replaceChildren(icon(document.documentElement.dataset.workspaceTheme === 'dark' ? 'sun' : 'moon')); })).observe(document.documentElement, {attributes:true, attributeFilter:['data-workspace-theme']});
  document.querySelectorAll('[data-theme-toggle]').forEach(control => control.addEventListener('click', () => window.AscendTheme.set(document.documentElement.dataset.workspaceTheme === 'dark' ? 'light' : 'dark')));
  const menu = document.querySelector('.site-menu-toggle'), nav = document.getElementById('site-navigation');
  if (menu && nav) {
    const close = () => { nav.classList.remove('is-open'); menu.setAttribute('aria-expanded','false'); menu.setAttribute('aria-label','Open navigation'); };
    menu.addEventListener('click', () => { const open = menu.getAttribute('aria-expanded') !== 'true'; nav.classList.toggle('is-open',open); menu.setAttribute('aria-expanded',String(open)); menu.setAttribute('aria-label',open ? 'Close navigation' : 'Open navigation'); });
    nav.addEventListener('click', event => { if (event.target.closest('a')) close(); });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') { close(); menu.focus(); } });
    document.addEventListener('click', event => { if (!event.target.closest('.site-header')) close(); });
    matchMedia('(min-width:651px)').addEventListener('change', close);
  }
  const page = document.documentElement.dataset.sitePage;
  document.querySelectorAll('[data-nav-page]').forEach(link => { if (link.dataset.navPage === page || (page === 'track' && link.dataset.navPage === 'tracks')) link.setAttribute('aria-current','page'); });
  if (page) document.title = ({home:'Small steps. Real skills.',tracks:'Explore learning tracks',how:'How Ascend works',privacy:'Privacy & your data'}[page] || 'Learning track') + ' · Ascend';
  async function accountLinks() {
    const options = await siteOptions();
    let account = null;
    if (options.auth_mode === 'single') document.querySelectorAll('[data-sign-in]').forEach(link => { link.hidden = true; });
    else if (window.AscendSession.get()) {
      const token = window.AscendSession.get();
      try {
        const result = await request('account', undefined, 'GET', {Authorization:`Bearer ${token}`});
        if (token !== window.AscendSession.get()) return;
        account = result;
      } catch (error) { if (error.status === 401 && token === window.AscendSession.get()) window.AscendSession.clear(); }
    }
    if (account || options.auth_mode === 'single') {
      document.querySelectorAll('[data-workspace-link]').forEach(link => {
        link.replaceChildren(element('span','Open workspace','site-header-cta-label'),icon('arrow'));
        link.setAttribute('aria-label','Open workspace');
      });
      if (account) document.querySelectorAll('[data-sign-in]').forEach(link => { link.textContent = 'My account'; link.href = '/app#profile'; });
    }
    document.querySelectorAll('[data-sign-out]').forEach(control => { control.hidden = !account; });
    document.documentElement.dataset.siteAccount = account ? 'signed-in' : options.auth_mode === 'single' ? 'local' : 'guest';
    const faq = document.getElementById('account-faq');
    if (faq && options.auth_mode === 'single') faq.textContent = 'This private workspace uses your local learning account, so you can open it directly. Your notes and progress stay in this Ascend installation.';
    else if (faq) faq.textContent = options.registration ? 'This shared workspace uses a username and password. You can create an account on the auth page. You do not need an email address; save your recovery code to keep a way back into your account.' : 'This shared workspace uses a username and password. The person managing the workspace creates your account. Use those credentials to sign in and keep your learning progress together.';
  }
  if (page) accountLinks().catch(() => { /* Public discovery remains useful if account options are unavailable. */ });
  document.querySelectorAll('[data-sign-out]').forEach(control => control.addEventListener('click', async () => {
    if (control.disabled) return;
    control.disabled = true; control.setAttribute('aria-busy','true');
    const token = window.AscendSession.get();
    try {
      if (token) {
        try { await request('logout',{},'POST',{Authorization:`Bearer ${token}`}); }
        catch (error) { if (error.status !== 401) throw error; }
      }
      if (token !== window.AscendSession.get()) return;
      window.AscendSession.clear();
      const next = new URLSearchParams(location.search).get('next') || '/app#today';
      location.assign(window.AscendSession.signInUrl('signed-out',next));
    } catch (error) {
      const message = element('p',error.message,'site-message site-toast'); message.setAttribute('role','alert');
      document.querySelector('.site-toast')?.remove(); document.body.append(message);
    } finally { control.disabled = false; control.removeAttribute('aria-busy'); }
  }));
  function initializePreview() {
    const tabs = [...document.querySelectorAll('[data-preview]')];
    const select = control => {
      for (const tab of tabs) {
        const active = tab === control;
        tab.setAttribute('aria-selected',String(active)); tab.tabIndex = active ? 0 : -1;
        document.getElementById(tab.getAttribute('aria-controls')).hidden = !active;
      }
    };
    for (const tab of tabs) {
      tab.addEventListener('click',() => select(tab));
      tab.addEventListener('keydown',event => {
        if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
        event.preventDefault();
        const index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (tabs.indexOf(tab) + (event.key === 'ArrowLeft' ? -1 : 1) + tabs.length) % tabs.length;
        select(tabs[index]); tabs[index].focus();
      });
    }
    document.getElementById('preview-copy-command').addEventListener('click',async () => {
      const code = document.querySelector('.product-terminal code'), command = code.textContent.replace(/^\$\s*/,'').trim();
      const status = document.getElementById('preview-copy-status');
      try { await navigator.clipboard.writeText(command); status.textContent = 'Example command copied.'; }
      catch {
        const range = document.createRange(); range.selectNodeContents(code);
        const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range);
        status.textContent = 'Command selected. Copy it to try with your local service.';
      }
    });
  }
  async function loadHome() {
    const data = await request('catalog');
    const selected = ['devops-service-foundations','ethical-hacking-foundations','io-linux-network'].map(id => data.tracks.find(track => track.id === id)).filter(Boolean);
    document.getElementById('featured-tracks').replaceChildren(...selected.map(trackCard));
    document.getElementById('home-catalog-total').textContent = `${data.tracks.length} tracks to explore`;
    document.getElementById('product-track-count').textContent = data.tracks.length.toLocaleString();
    document.getElementById('product-task-count').textContent = data.tracks.reduce((count,track) => count + track.nodes,0).toLocaleString();
    const track = await request('catalog/devops-service-foundations').catch(() => null);
    if (!track) return;
    const levels = track.levels.filter(level => level.lane === 'main'), first = levels[0]?.challenges[0];
    document.getElementById('preview-category').textContent = track.title;
    if (first) {
      document.getElementById('preview-task').textContent = first.title;
      document.getElementById('preview-description').textContent = first.preview;
    }
    document.getElementById('preview-level-count').textContent = `${levels.length} levels`;
    document.getElementById('preview-path').replaceChildren(...levels.slice(0,3).map((level,index) => {
      const item = element('li'), copy = element('div');
      copy.append(element('strong',level.title),element('small',`${level.challenges.length} practical tasks`));
      item.append(element('span',String(index + 1).padStart(2,'0')),copy); return item;
    }));
  }
  async function loadCatalog() {
    const root = document.getElementById('track-results'), search = document.getElementById('track-search'), select = document.getElementById('track-category'), form = document.getElementById('track-search-form');
    const data = await request('catalog'), params = new URLSearchParams(location.search);
    const categories = ['Cybersecurity', ...data.categories];
    for (const category of categories) { const option = element('option', category); option.value = category; select.append(option); }
    search.value = (params.get('q') || '').slice(0,120); select.value = categories.includes(params.get('category')) ? params.get('category') : '';
    const cyber = new Set(['Foundations','Offensive','Defensive','Engineering','Specialist','Practice']);
    const draw = (updateUrl = true) => {
      const query = search.value.trim().toLowerCase(), category = select.value;
      const matches = data.tracks.filter(track => (!category || track.category === category || (category === 'Cybersecurity' && cyber.has(track.category))) && [track.title,track.id,track.description,...track.aliases].join(' ').toLowerCase().includes(query));
      matches.sort((a,b) => a.category.localeCompare(b.category) || (a.track_order || 100) - (b.track_order || 100) || a.title.localeCompare(b.title));
      root.replaceChildren(...matches.map(trackCard)); root.setAttribute('aria-busy','false');
      if (!matches.length) {
        const panel = empty('No tracks found.', 'Try a broader subject, a different keyword, or clear the filters.');
        const reset = element('button','Show all tracks','secondary'); reset.type = 'button'; reset.addEventListener('click',clear); panel.append(reset); root.append(panel);
      }
      document.getElementById('track-count').textContent = `${matches.length} ${matches.length === 1 ? 'track' : 'tracks'}${query || category ? ' found' : ' to explore'}`;
      document.getElementById('clear-track-filters').hidden = !query && !category;
      document.querySelectorAll('[data-category]').forEach(control => control.setAttribute('aria-pressed',String(control.dataset.category === category)));
      if (updateUrl) { const next = new URLSearchParams(); if (search.value.trim()) next.set('q',search.value.trim()); if (category) next.set('category',category); history.replaceState(null,'','/tracks' + (next.size ? '?' + next : '')); }
    };
    const clear = () => { search.value = ''; select.value = ''; draw(); search.focus(); };
    let timer;
    search.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(draw,180); });
    select.addEventListener('change', () => draw());
    form.addEventListener('submit', event => { event.preventDefault(); clearTimeout(timer); draw(); });
    document.getElementById('clear-track-filters').addEventListener('click',clear);
    document.querySelectorAll('[data-category]').forEach(control => control.addEventListener('click', () => { select.value = control.dataset.category; draw(); }));
    window.addEventListener('popstate', () => { const current = new URLSearchParams(location.search); search.value = current.get('q') || ''; select.value = current.get('category') || ''; draw(false); });
    draw(false);
  }
  async function loadTrack() {
    const root = document.getElementById('track-detail'), id = location.pathname.split('/')[2];
    const track = await request('catalog/' + encodeURIComponent(id));
    document.title = track.title + ' · Ascend';
    root.querySelector('.site-loading').remove();
    const hero = element('div', undefined, 'site-detail-hero'), copy = element('div');
    copy.append(element('p',track.category.toUpperCase(),'eyebrow'),element('h1',track.title),element('p',track.description));
    const aside = element('div',undefined,'site-detail-aside'), meta = element('div',undefined,'site-track-meta');
    meta.append(element('span',`${track.main_levels} levels`),element('span',`${track.nodes} tasks`));
    const add = element('a','Add to my tracks','site-button'); add.href = `/app?track=${encodeURIComponent(track.id)}#more`; add.append(icon('arrow'));
    aside.append(meta,element('p',track.reviewed ? 'Reviewed curriculum' : 'Draft curriculum · Read before starting'),add,element('p','Opens track setup in your workspace. You choose when to start.'));
    hero.append(copy,aside);
    const content = element('div',undefined,'site-detail-content'), lessons = element('section'); lessons.append(element('h2','Your path through this track'));
    const list = element('ol',undefined,'site-detail-levels');
    for (const level of track.levels.filter(level => level.lane === 'main')) {
      const item = element('li'), body = element('div'); body.append(element('h3',level.title),element('p',`${level.challenges.length} practical ${level.challenges.length === 1 ? 'task' : 'tasks'}`));
      const details = element('details'), summary = element('summary','See what you’ll work on'), tasks = element('ul');
      for (const challenge of level.challenges) { const task = element('li'); task.append(element('strong',challenge.title)); if (challenge.preview) task.append(element('p',challenge.preview)); tasks.append(task); }
      details.append(summary,tasks); body.append(details); item.append(body); list.append(item);
    }
    lessons.append(list);
    const info = element('aside'), entry = element('article',undefined,'card'); entry.append(element('h2','Before you begin'),element('p',track.entry || 'Read the opening challenge’s setup and choose your starting point based on the skills you can already demonstrate.'));
    info.append(entry);
    if (track.limits) { const limits = element('article',undefined,'card'); limits.append(element('h2','Your practice environment'),element('p',track.limits)); info.append(limits); }
    const flexibility = element('article',undefined,'card'); flexibility.append(element('h2','Go at your own pace'),element('p','Each challenge has a concrete finish line. Save partial learning, return to your notes, and use worked examples when you need a little guidance.'));
    info.append(flexibility); content.append(lessons,info); root.append(hero,content); root.setAttribute('aria-busy','false');
  }
  const fail = (id,error) => {
    const root = document.getElementById(id); root.replaceChildren(empty(error.status === 404 ? 'Track not found.' : 'The learning library could not load.',error.status === 404 ? 'This track isn’t in the bundled library. Explore the available tracks to find your next direction.' : error.message,'Browse all tracks','/tracks')); root.setAttribute('aria-busy','false');
    if (error.status !== 404) { const retry = element('button','Try again','secondary'); retry.addEventListener('click',()=>location.reload()); root.firstChild.append(retry); }
  };
  if (page === 'home') { initializePreview(); loadHome().catch(error => fail('featured-tracks',error)); }
  if (page === 'tracks') loadCatalog().catch(error => { document.getElementById('track-count').textContent = 'Tracks are temporarily unavailable.'; fail('track-results',error); });
  if (page === 'track') loadTrack().catch(error => fail('track-detail',error));
  return {element,icon,request,siteOptions,download,fillIcons};
})();
