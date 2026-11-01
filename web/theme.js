document.documentElement.dataset.boot = 'loading';
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
window.AscendBoot.deadline = setTimeout(() => window.AscendBoot.finish(true), 5000);
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
