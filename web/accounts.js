"use strict";
(() => {
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  async function mount(host, {account, api, replaceToken, signOut}) {
    if (!host) return;
    host.hidden = true; host.replaceChildren();
    if (!account.account_management || account.auth_mode !== 'multi') return;
    const data = await api('account/security');
    host.append(element('h2', 'Account security'));
    host.append(element('p', 'Your learning history stays with this account. Manage your password, recovery code, and signed-in sessions here.', 'field-help'));
    const feedback = element('p', '', 'account-security-status'); feedback.setAttribute('role', 'status');
    const report = (message, error = false) => {
      feedback.textContent = message; feedback.classList.toggle('error', error);
      feedback.setAttribute('role', error ? 'alert' : 'status');
    };
    const operation = async (control, action) => {
      if (control.disabled) return;
      control.disabled = true; control.setAttribute('aria-busy', 'true');
      try { await action(); } catch (error) { report(error.message, true); }
      finally { control.disabled = false; control.removeAttribute('aria-busy'); }
    };
    const form = element('form');
    form.append(element('h3', 'Change password'));
    const passwordField = (id, label, autocomplete) => {
      const caption = element('label', label); caption.htmlFor = id;
      const input = element('input'); input.id = id; input.type = 'password'; input.required = true;
      input.autocomplete = autocomplete; input.maxLength = 1024;
      if (autocomplete === 'new-password') input.minLength = 12;
      form.append(caption, input); return input;
    };
    const current = passwordField('account-current-password', 'Current password', 'current-password');
    const next = passwordField('account-new-password', 'New password', 'new-password');
    const confirm = passwordField('account-confirm-password', 'Confirm new password', 'new-password');
    form.append(element('p', 'Use at least 12 characters. Changing your password signs out every other browser and CLI session.', 'field-help'));
    const change = element('button', 'Change password'); change.type = 'submit'; form.append(change);
    const sessionList = element('div', undefined, 'account-sessions');
    const renderSessions = async () => {
      const snapshot = await api('account/security');
      sessionList.replaceChildren();
      for (const session of snapshot.sessions) {
        const row = element('article', undefined, 'account-session');
        row.append(element('h4', session.current ? `${session.label} · This session` : session.label));
        row.append(element('p', `Signed in ${new Date(session.created_at).toLocaleString()} · Expires ${new Date(session.expires_at).toLocaleString()}`, 'field-help'));
        const revoke = element('button', session.current ? 'Sign out this session' : 'Sign out session', 'secondary'); revoke.type = 'button';
        revoke.setAttribute('aria-label', session.current ? 'Sign out this session' : `Sign out ${session.label}`);
        revoke.addEventListener('click', () => operation(revoke, async () => {
          const result = await api(`account/sessions/${session.id}`, {}, 'DELETE');
          if (result.logged_out) { signOut(); return; }
          await renderSessions(); report('Session signed out.');
        }));
        row.append(revoke); sessionList.append(row);
      }
    };
    form.addEventListener('submit', event => {
      event.preventDefault();
      if (next.value !== confirm.value) { report('The new passwords do not match.', true); confirm.focus(); return; }
      operation(change, async () => {
        const result = await api('account/password', {current_password: current.value, new_password: next.value});
        replaceToken(result.token); current.value = ''; next.value = ''; confirm.value = '';
        await renderSessions(); report('Password changed. Other sessions are signed out; this session stays open.');
      });
    });
    host.append(form, feedback, element('h3', 'Signed-in sessions'));
    host.append(element('p', `Sessions expire ${data.session_lifetime_days} days after sign-in. You can keep up to ${data.max_sessions} sessions. Session labels describe the client; they do not establish a device identity.`, 'field-help'));
    const revokeOthers = element('button', 'Sign out other sessions', 'secondary'); revokeOthers.type = 'button';
    revokeOthers.addEventListener('click', () => operation(revokeOthers, async () => {
      const result = await api('account/sessions/revoke-others', {});
      await renderSessions(); report(result.revoked ? `${result.revoked} other session${result.revoked === 1 ? '' : 's'} signed out.` : 'No other sessions are signed in.');
    }));
    host.append(revokeOthers, sessionList);
    const recovery = element('form', undefined, 'account-recovery');
    recovery.append(element('h3', 'Recovery code'), element('p', data.recovery_code_configured ? 'Your account has a recovery code. Replacing it makes the previous code unusable. Keep the replacement somewhere private.' : 'Create a private, one-use code to reset your password if you lose access. You can also ask your workspace administrator for help.', 'field-help'));
    const recoveryLabel = element('label', 'Current password for recovery code'); recoveryLabel.htmlFor = 'account-recovery-password';
    const recoveryPassword = element('input'); recoveryPassword.id = recoveryLabel.htmlFor; recoveryPassword.type = 'password'; recoveryPassword.required = true; recoveryPassword.maxLength = 1024; recoveryPassword.autocomplete = 'current-password';
    const createCode = element('button', data.recovery_code_configured ? 'Replace recovery code' : 'Create recovery code'); createCode.type = 'submit';
    const codeResult = element('section', undefined, 'account-recovery-result'); codeResult.hidden = true;
    const codeLabel = element('label', 'New recovery code'); codeLabel.htmlFor = 'account-recovery-code';
    const code = element('input', undefined, 'account-recovery-code'); code.id = codeLabel.htmlFor; code.readOnly = true; code.autocomplete = 'off'; code.spellcheck = false;
    const actions = element('div', undefined, 'card-actions');
    const download = element('button', 'Download recovery code', 'secondary'); download.type = 'button';
    download.addEventListener('click', () => {
      const url = URL.createObjectURL(new Blob([`Ascend recovery code\nWorkspace: ${location.origin}\nUsername: ${account.username}\n\n${code.value}\n\nKeep this private. It can reset your password once. A reset replaces the code and signs out existing sessions.\n`], {type:'text/plain;charset=utf-8'}));
      const link = element('a'); link.href = url; link.download = `ascend-recovery-${account.username}.txt`; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    const dismiss = element('button', 'I saved this code', 'secondary'); dismiss.type = 'button'; dismiss.addEventListener('click', () => { code.value = ''; codeResult.hidden = true; });
    actions.append(download, dismiss);
    codeResult.append(element('h4', 'Keep a way back in.'), element('p', 'Save this code somewhere safe. It is shown here only until you leave this page or dismiss it.', 'field-help'), codeLabel, code, actions);
    recovery.append(recoveryLabel, recoveryPassword, createCode, codeResult);
    recovery.addEventListener('submit', event => {
      event.preventDefault();
      operation(createCode, async () => {
        const result = await api('account/recovery-code', {current_password:recoveryPassword.value});
        recoveryPassword.value = ''; code.value = result.recovery_code; codeResult.hidden = false; createCode.textContent = 'Replace recovery code';
        report('Recovery code created. Save it somewhere private. Any previous code no longer works.'); code.focus();
      });
    });
    host.append(recovery);
    await renderSessions(); host.hidden = false;
  }
  window.AscendAccounts = {mount};
})();
