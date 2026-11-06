"use strict";
// The auth page and workspace share credentials and a full-document identity boundary.
window.AscendSession = (() => {
  const read = (storage, key) => { try { return window[storage].getItem(key); } catch { return null; } };
  const get = () => read('sessionStorage', 'ascend-token') || read('localStorage', 'ascend-token');
  const remembered = () => Boolean(read('localStorage', 'ascend-token'));
  const set = (token, remember = remembered()) => {
    try {
      sessionStorage.setItem('ascend-token', token);
      if (remember) localStorage.setItem('ascend-token', token);
      else localStorage.removeItem('ascend-token');
    } catch {
      if (read('sessionStorage', 'ascend-token') !== token) throw new Error('Allow browser storage to sign in to your workspace.');
      if (remember) throw new Error('This browser could not remember your session. Turn off “Remember me” and try again.');
    }
  };
  const clear = () => {
    for (const storage of ['sessionStorage', 'localStorage']) {
      try { window[storage].removeItem('ascend-token'); } catch { /* Storage may be restricted. */ }
    }
  };
  const safeNext = candidate => {
    if (!candidate || !candidate.startsWith('/') || candidate.startsWith('//') || /[\\\x00-\x20]/.test(candidate)) return '/app#today';
    try {
      const url = new URL(candidate, location.origin);
      if (url.origin !== location.origin || !['/app', '/app/'].includes(url.pathname)) return '/app#today';
      return url.pathname + url.search + url.hash;
    } catch { return '/app#today'; }
  };
  const signInUrl = (reason = '', next = location.pathname + location.search + location.hash) => {
    const params = new URLSearchParams({next:safeNext(next)});
    if (reason) params.set('reason', reason);
    return '/auth?' + params;
  };
  const requireSignIn = reason => {
    clear();
    location.replace(signInUrl(reason));
  };
  const authorizeWorkspace = async () => {
    // The installed guide remains readable without a connection or account.
    if (location.hash.startsWith('#docs')) return true;
    let response;
    try { response = await fetch('/api/health', {cache:'no-store', signal:AbortSignal.timeout(10000)}); }
    catch { throw new Error('The server is not responding. Check your connection and reload your workspace.'); }
    if (!response.ok) throw new Error('The workspace could not connect to its server.');
    const health = await response.json();
    if (health.auth_mode === 'single') return true;
    if (!get()) { location.replace(signInUrl()); return false; }
    const token = get();
    const account = await fetch('/api/account', {headers:{Authorization:`Bearer ${token}`}, cache:'no-store', signal:AbortSignal.timeout(10000)});
    if (token !== get()) return false;
    if (account.status === 401) { requireSignIn('expired'); return false; }
    if (!account.ok) throw new Error('Your account could not load. Reload to try again.');
    return true;
  };
  window.addEventListener('storage', event => {
    // A remembered session changing in another tab must rehydrate the whole account.
    if (event.key === 'ascend-token' && event.oldValue && read('sessionStorage', 'ascend-token') === event.oldValue) {
      try { sessionStorage.removeItem('ascend-token'); } catch { /* No tab credential remains. */ }
      if (document.documentElement.dataset.app === 'workspace') location.reload();
      else window.dispatchEvent(new Event('ascend-session-change'));
    }
  });
  return {get, set, clear, remembered, safeNext, signInUrl, requireSignIn, authorizeWorkspace};
})();
