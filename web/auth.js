"use strict";
(() => {
  const {element, icon, request, siteOptions, download} = window.AscendSite;
  const session = window.AscendSession;
  const $ = selector => document.querySelector(selector);
  const params = new URLSearchParams(location.search), next = session.safeNext(params.get('next'));
  let options, mode = 'signin', pending = null, checking = false;
  const feedback = $('#auth-feedback');
  const report = (message, info = false) => {
    feedback.textContent = message; feedback.hidden = false; feedback.dataset.kind = info ? 'info' : 'error';
    feedback.setAttribute('role', info ? 'status' : 'alert');
  };
  const clearFeedback = () => { feedback.hidden = true; feedback.textContent = ''; $('#auth-form').querySelectorAll('[aria-invalid]').forEach(field => field.removeAttribute('aria-invalid')); };
  const fieldError = (field, message) => { report(message); field.setAttribute('aria-invalid','true'); field.focus(); };
  const title = (heading,intro) => { $('#auth-heading').textContent = heading; $('#auth-intro').textContent = intro; document.title = heading.replace(/\.$/,'') + ' · Ascend'; };
  const submitLabel = label => { $('#auth-submit').replaceChildren(document.createTextNode(label),icon('arrow')); };
  function setMode(requested, updateUrl = true) {
    if (!options || options.auth_mode === 'single' || $('#auth-submit').disabled) return;
    clearFeedback(); pending = null; $('#auth-code-result').hidden = true; $('#auth-saved-code').value = '';
    mode = ['signin','signup','recover','help'].includes(requested) ? requested : 'signin';
    if (mode === 'signup' && !options.registration) { mode = 'signin'; report('Accounts for this workspace are provided by its administrator. Ask them for your username and password.',true); }
    $('#auth-forms').hidden = false; $('#auth-session').hidden = true;
    const recover = mode === 'recover' || mode === 'help', signup = mode === 'signup';
    const supported = !recover || (mode !== 'help' && options.recovery);
    $('#auth-form').hidden = !supported; $('#auth-operator-help').hidden = supported;
    $('#auth-sign-up-tab').hidden = !options.registration;
    document.querySelectorAll('[data-auth-mode]').forEach(control => { if (control.closest('.auth-tabs')) control.setAttribute('aria-pressed',String(control.dataset.authMode === mode)); });
    $('#auth-code-field').hidden = !recover; $('#auth-recovery-code').required = recover && supported;
    $('#auth-confirm-field').hidden = mode === 'signin'; $('#auth-confirm').required = mode !== 'signin';
    $('#auth-timezone-field').hidden = !signup; $('#auth-remember-field').hidden = recover;
    $('#auth-username-help').hidden = !signup; $('#auth-password-help').hidden = mode === 'signin';
    $('#auth-password-label').textContent = recover ? 'New password' : 'Password';
    $('#auth-password').autocomplete = mode === 'signin' ? 'current-password' : 'new-password';
    $('#auth-password').placeholder = mode === 'signin' ? 'Your password' : 'At least 12 characters';
    $('#auth-forgot-password').hidden = mode !== 'signin';
    $('#auth-forgot-password').href = '/auth?' + new URLSearchParams({mode:'recover',next});
    $('#auth-password').value = ''; $('#auth-confirm').value = ''; $('#auth-caps-lock').hidden = true;
    document.querySelectorAll('[data-toggle-password]').forEach(control => { document.getElementById(control.dataset.togglePassword).type = 'password'; control.setAttribute('aria-pressed','false'); control.setAttribute('aria-label',control.dataset.togglePassword === 'auth-password' ? 'Show password' : 'Show confirmation password'); });
    if (signup) { title('Your first step.','A username, a little curiosity, and a place to begin.'); submitLabel('Create account'); }
    else if (recover) { title('Find your way back.','Recover access to your saved path, notes, and progress.'); submitLabel('Reset password'); }
    else { title('Welcome back.','Pick up where your curiosity left off.'); submitLabel('Sign in'); }
    $('#auth-account-note').textContent = signup ? 'No email address needed. Save your recovery code after signup.' : recover ? 'Your code works once. A reset signs out existing sessions and gives you a new recovery code.' : options.registration ? 'New here? Choose Create account to start your own learning path.' : 'Use the account provided by your workspace administrator.';
    if (updateUrl) { const query = new URLSearchParams({next}); if (mode !== 'signin') query.set('mode',mode); history.replaceState(null,'','/auth?' + query); }
  }
  function showRecoveryCode(code, context) {
    pending = context;
    $('#auth-forms').hidden = true; $('#auth-session').hidden = true; $('#auth-code-result').hidden = false;
    $('#auth-saved-code').value = code; $('#auth-code-saved').checked = false; $('#auth-code-continue').disabled = true;
    $('#auth-code-status').textContent = '';
    if (context.kind === 'signup') {
      title('One step closer.','Your account is ready. Keep a way back in before you begin.');
      $('#auth-code-heading').textContent = 'Save your recovery code.';
      $('#auth-code-intro').textContent = 'This private code can reset your password once. Save it in your password manager or download it somewhere safe. It is not stored in your browser.';
      $('#auth-code-continue').replaceChildren(document.createTextNode('Continue to workspace'),icon('arrow'));
    } else {
      title('You’re back on track.','Your password has been reset and earlier sessions are signed out.');
      $('#auth-code-heading').textContent = 'Keep your new recovery code.';
      $('#auth-code-intro').textContent = 'Your previous code has been used. Save this replacement somewhere private so you can recover your account again.';
      $('#auth-code-continue').replaceChildren(document.createTextNode('Back to sign in'),icon('arrow'));
    }
    $('#auth-code-result').scrollIntoView({block:'nearest',behavior:'instant'});
    $('#auth-saved-code').focus();
  }
  function fillTimezones() {
    let current = 'UTC';
    try { current = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'; } catch { /* UTC remains valid. */ }
    const zones = new Set(options.timezones || ['UTC',...(Intl.supportedValuesOf?.('timeZone') || [])]);
    if (!zones.has(current)) {
      // Browser ICU may return an older alias, such as Asia/Calcutta, while
      // the server ships its canonical IANA zone, Asia/Kolkata.
      current = [...zones].find(zone => {
        try { return Intl.DateTimeFormat('en',{timeZone:zone}).resolvedOptions().timeZone === current; }
        catch { return false; }
      }) || 'UTC';
    }
    $('#auth-timezone').replaceChildren(...[...zones].sort().map(zone => { const option = element('option',zone.replaceAll('_',' ')); option.value = zone; return option; }));
    $('#auth-timezone').value = current;
  }
  async function initialize() {
    if (checking) return;
    checking = true; $('#auth-loading').hidden = false; clearFeedback();
    try {
      options = await siteOptions();
      if (options.auth_mode === 'single') {
        title('Your workspace is ready.','One small step is a good place to start.');
        $('#auth-local').hidden = false; $('#auth-local-continue').href = next;
        $('#auth-forms').hidden = true;
        return;
      }
      fillTimezones();
      const desired = params.get('mode') || (location.pathname === '/signup' ? 'signup' : 'signin');
      if (session.get()) {
        const token = session.get();
        try {
          const account = await request('account',undefined,'GET',{Authorization:`Bearer ${token}`});
          if (token !== session.get()) return;
          title('Ready for another step?','Your learning workspace is a click away.');
          $('#auth-session-name').textContent = `You’re signed in as ${account.username}.`;
          $('#auth-session-continue').href = next; $('#auth-session').hidden = false; return;
        } catch (error) { if (error.status === 401) session.clear(); else throw error; }
      }
      setMode(desired,false);
      if (params.get('reason') === 'expired') report('Your session ended. Sign in again to return to your work. Unsaved browser drafts retain their original account.',true);
      else if (params.get('reason') === 'signed-out') report('You’re signed out. Your saved learning is ready when you return.',true);
    } catch (error) {
      report(error.message);
      const retry = element('button','Try again','secondary'); retry.type = 'button'; retry.addEventListener('click',initialize); feedback.append(element('br'),retry);
    } finally { checking = false; $('#auth-loading').hidden = true; }
  }
  document.querySelectorAll('[data-auth-mode]').forEach(control => control.addEventListener('click', () => setMode(control.dataset.authMode)));
  $('#auth-forgot-password').addEventListener('click',event => { event.preventDefault(); setMode('recover'); if (!$('#auth-form').hidden) $('#auth-username').focus(); });
  document.querySelectorAll('[data-toggle-password]').forEach(control => control.addEventListener('click', () => {
    const field = document.getElementById(control.dataset.togglePassword), show = field.type === 'password';
    field.type = show ? 'text' : 'password'; control.setAttribute('aria-pressed',String(show));
    const confirmation = control.dataset.togglePassword === 'auth-confirm';
    control.setAttribute('aria-label',`${show ? 'Hide' : 'Show'} ${confirmation ? 'confirmation password' : 'password'}`);
  }));
  $('#auth-password').addEventListener('keyup',event => { $('#auth-caps-lock').hidden = !event.getModifierState('CapsLock'); });
  $('#auth-password').addEventListener('blur',() => { $('#auth-caps-lock').hidden = true; });
  $('#auth-form').addEventListener('input',event => { if (event.target.hasAttribute('aria-invalid')) event.target.removeAttribute('aria-invalid'); });
  $('#auth-form').addEventListener('submit',async event => {
    event.preventDefault();
    if ($('#auth-submit').disabled || $('#auth-form').hidden || !options) return;
    clearFeedback();
    const username = $('#auth-username').value.trim(), password = $('#auth-password').value;
    if (!username) { fieldError($('#auth-username'),'Enter your username.'); return; }
    if (mode === 'signup' && !/^[a-zA-Z0-9_-]{3,40}$/.test(username)) { fieldError($('#auth-username'),'Choose a username with 3–40 letters, numbers, underscores, or hyphens.'); return; }
    if (!password) { fieldError($('#auth-password'),mode === 'recover' ? 'Choose a new password.' : 'Enter your password.'); return; }
    if (mode !== 'signin' && [...password].length < 12) { fieldError($('#auth-password'),'Use at least 12 characters for your password.'); return; }
    if (mode !== 'signin' && password !== $('#auth-confirm').value) { fieldError($('#auth-confirm'),'The passwords do not match. Type the same password again.'); return; }
    if (mode === 'recover' && !$('#auth-recovery-code').value.trim()) { fieldError($('#auth-recovery-code'),'Enter the recovery code you saved.'); return; }
    const submit = $('#auth-submit'); submit.disabled = true; submit.setAttribute('aria-busy','true');
    const submittedMode = mode, remember = $('#auth-remember').checked;
    // Prevent switching modes while a write is in flight.
    document.querySelectorAll('[data-auth-mode]').forEach(control => { control.disabled = true; });
    try {
      if (submittedMode === 'signup') {
        const result = await request('register',{username,password,timezone:$('#auth-timezone').value,label:remember ? 'Remembered browser' : 'Browser tab'});
        $('#auth-password').value = ''; $('#auth-confirm').value = '';
        showRecoveryCode(result.recovery_code,{kind:'signup',username,token:result.token,remember});
      } else if (submittedMode === 'recover') {
        const result = await request('recover',{username,recovery_code:$('#auth-recovery-code').value.trim(),new_password:password});
        $('#auth-password').value = ''; $('#auth-confirm').value = ''; $('#auth-recovery-code').value = '';
        showRecoveryCode(result.recovery_code,{kind:'recover',username});
      } else {
        const result = await request('login',{username,password,label:remember ? 'Remembered browser' : 'Browser tab'});
        session.set(result.token,remember); $('#auth-password').value = ''; location.assign(next);
      }
    } catch (error) { report(error.message); }
    finally { submit.disabled = false; submit.removeAttribute('aria-busy'); document.querySelectorAll('[data-auth-mode]').forEach(control => { control.disabled = false; }); }
  });
  $('#auth-use-another').addEventListener('click',async () => {
    const control = $('#auth-use-another'); if (control.disabled) return; control.disabled = true;
    try { await request('logout',{},'POST',{Authorization:`Bearer ${session.get()}`}); session.clear(); setMode('signin'); }
    catch (error) { if (error.status === 401) { session.clear(); setMode('signin'); } else report(error.message); }
    finally { control.disabled = false; }
  });
  $('#auth-copy-code').addEventListener('click',async () => {
    try { await navigator.clipboard.writeText($('#auth-saved-code').value); $('#auth-code-status').textContent = 'Recovery code copied. Save it somewhere private.'; }
    catch { $('#auth-saved-code').focus(); $('#auth-saved-code').select(); $('#auth-code-status').textContent = 'Code selected. Copy it and save it somewhere private.'; }
  });
  $('#auth-download-code').addEventListener('click',() => {
    if (!pending) return;
    download(`ascend-recovery-${pending.username}.txt`,`Ascend recovery code\nWorkspace: ${location.origin}\nUsername: ${pending.username}\n\n${$('#auth-saved-code').value}\n\nKeep this private. It can reset your password once. A successful reset replaces this code and signs out existing sessions.\n`);
    $('#auth-code-status').textContent = 'Recovery code downloaded. Keep the file somewhere private.';
  });
  $('#auth-code-saved').addEventListener('change',() => { $('#auth-code-continue').disabled = !$('#auth-code-saved').checked; });
  $('#auth-code-continue').addEventListener('click',() => {
    if (!pending || !$('#auth-code-saved').checked) return;
    const context = pending;
    if (context.kind === 'signup') {
      try { session.set(context.token,context.remember); $('#auth-saved-code').value = ''; pending = null; location.assign(next); }
      catch (error) { report(error.message); }
    } else {
      session.clear(); setMode('signin'); $('#auth-username').value = context.username;
      report('Password reset. Sign in with your new password to return to your workspace.',true); $('#auth-password').focus();
    }
  });
  window.addEventListener('ascend-session-change',()=>location.reload());
  initialize();
})();
