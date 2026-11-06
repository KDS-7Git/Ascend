"use strict";
(() => {
  const path = location.pathname.replace(/\/$/, '') || '/';
  const legacy = ['today','path','playground','activity','lab','attempts','stats','more','docs','profile','challenge'];
  if (['/', '/welcome'].includes(path) && legacy.includes(location.hash.slice(1).split('/')[0])) {
    location.replace('/app' + location.search + location.hash);
    return;
  }
  document.documentElement.dataset.sitePage = path.startsWith('/tracks/') ? 'track' : ({'/tracks':'tracks','/how-it-works':'how','/privacy':'privacy'}[path] || 'home');
})();
