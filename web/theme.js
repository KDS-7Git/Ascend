if (document.documentElement.dataset.app === 'workspace') document.documentElement.dataset.boot = 'loading';
// Startup decoration must never trap the workspace, including an older cached app.
window.AscendBoot = {
  finish(failed = false) {
    delete document.documentElement.dataset.boot;
    const loader = document.getElementById('app-loader');
    if (loader) loader.hidden = true;
    clearTimeout(window.AscendBoot.deadline);
    if (!failed && document.getElementById('notice')?.dataset.bootNotice) {
      document.getElementById('notice').hidden = true;
      delete document.getElementById('notice').dataset.bootNotice;
    }
    if (failed) {
      const notice = document.getElementById('notice');
      const message = notice?.querySelector('.notice-message');
      if (notice && message) {
        message.textContent = 'Startup did not finish. ';
        const retry = document.createElement('a');
        retry.href = location.href; retry.textContent = 'Reload the workspace';
        message.append(retry); notice.dataset.bootNotice = 'true'; notice.hidden = false;
      }
    }
  }
};
if (document.documentElement.dataset.app === 'workspace') window.AscendBoot.deadline = setTimeout(() => window.AscendBoot.finish(true), 5000);
window.addEventListener('error', event => {
  if (event.target?.tagName === 'SCRIPT') window.AscendBoot.finish(true);
}, true);
// Apply the saved preference before first paint. No network or account is needed.
try {
  const theme = localStorage.getItem('ascend-theme');
  if (theme === 'light' || theme === 'dark') document.documentElement.dataset.theme = theme;
} catch { /* System color preference remains available when storage is blocked. */ }
try {
  if (localStorage.getItem('ascend-motion') === 'off') document.documentElement.dataset.motion = 'off';
} catch { /* The device preference is still respected. */ }

// Public pages and the workspace resolve the same saved/system theme.
(() => {
  const root = document.documentElement;
  const system = matchMedia('(prefers-color-scheme: dark)');
  const sync = () => {
    root.dataset.workspaceTheme = root.dataset.theme === 'dark' || (!root.dataset.theme && system.matches) ? 'dark' : 'light';
    document.querySelectorAll('[data-theme-toggle]').forEach(control => {
      const dark = root.dataset.workspaceTheme === 'dark';
      control.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
      control.setAttribute('aria-pressed', String(dark));
    });
  };
  const set = theme => {
    if (theme === 'light' || theme === 'dark') root.dataset.theme = theme;
    else delete root.dataset.theme;
    try { localStorage.setItem('ascend-theme', theme); } catch { /* Honor the choice for this page. */ }
    sync();
  };
  new MutationObserver(sync).observe(root, {attributes:true, attributeFilter:['data-theme']});
  system.addEventListener('change', sync);
  window.addEventListener('storage', event => {
    if (event.key === 'ascend-theme') {
      if (event.newValue === 'light' || event.newValue === 'dark') root.dataset.theme = event.newValue;
      else delete root.dataset.theme;
      sync();
    }
  });
  window.AscendTheme = {set, sync};
  sync();
})();
