# Account management

Account controls are implemented and **off by default**, as requested for dashboard testing. `AUTH_MODE=single` continues to select the existing local account without login. `ASCEND_ACCOUNT_MANAGEMENT=1` has no effect in single mode. No existing profile was converted, new real user created, or running service restarted during implementation.

When explicitly enabled later, multi-user mode provides username/password login, logout, password changes, a list of signed-in sessions, individual session revocation and signing out other sessions. Password changes require the current password and replace the current token while revoking every earlier token. Login changes reload the document so a previous account's pending notebook cannot be sent under the next account's credentials. A delayed response for an earlier token cannot reopen sign-in after token rotation.

Passwords use scrypt and must contain 12–1024 characters. Only token hashes are stored. Sessions expire 30 days after sign-in; at most 20 remain per account. The session list exposes a separate revocation identifier, label and timestamps, not a bearer token or its stored hash. Labels are client-supplied descriptions, not proof of device identity.

Sign-in and current-password checks use bounded per-process throttling: 12 attempts per source/account in 15 minutes and 100 per source. Successful checks clear the account bucket. A multi-worker or public deployment should supply a shared edge limit appropriate to its topology; this implementation does not pretend an in-memory counter is a distributed control. Password checks and replacement hashes are computed before the SQLite write transaction, followed by a hash recheck inside it to prevent a concurrent password reset from being bypassed.

## Later testing in a separate profile

Use a new directory chosen for the test; this does not migrate the local dashboard's history:

```sh
.venv/bin/ascend-server --home /tmp/ascend-account-test user-add alice --timezone Asia/Kolkata
.venv/bin/ascend-server --home /tmp/ascend-account-test --auth-mode multi --account-management --port 8422
```

Open Profile after sign-in to use Account security. The equivalent environment setting is `ASCEND_ACCOUNT_MANAGEMENT=1` with `AUTH_MODE=multi`. Compose forwards this setting with a default of `0`; the private `.env` is not modified automatically.

Accounts are operator-provisioned. There is no public signup, email delivery, OAuth, organisation membership or pretend password-recovery form. Recovery is a real operator action against the chosen installation, using a password prompt that does not echo or place the password in shell history:

```sh
.venv/bin/ascend-server --home /tmp/ascend-account-test user-list
.venv/bin/ascend-server --home /tmp/ascend-account-test user-password alice
.venv/bin/ascend-server --home /tmp/ascend-account-test user-disable alice
.venv/bin/ascend-server --home /tmp/ascend-account-test user-enable alice
.venv/bin/ascend-server --home /tmp/ascend-account-test user-revoke alice
```

Disabling an account and password recovery revoke existing sessions while retaining its ID and learning data. Resetting a password also enables that named account. The implicit local account cannot be enabled or reset into a remotely usable account. Revocation stops subsequent requests; it does not cancel an operation already authenticated before the revocation.

## API and browser boundaries

With the feature off, the optional routes are absent from OpenAPI and unavailable. With the feature enabled in multi mode, every route requires the current bearer identity:

| Route | Operation |
| --- | --- |
| `GET /api/account/security` | Own sessions, expiry and supported limits |
| `POST /api/account/password` | Current/new password; returns a new token after atomic replacement |
| `POST /api/account/sessions/revoke-others` | Keep the calling token; revoke other tokens for this account |
| `DELETE /api/account/sessions/{id}` | Revoke one own session; an unknown or other-account ID returns 404 |

API responses remain uncached and browser writes retain origin checks. Unsynced notebook drafts stay keyed to their original account for recovery. Browser storage is not encrypted shared-device confidentiality: someone who controls the browser profile can inspect its local data. No other account receives that draft through a login transition.

Validation uses disposable profiles, synthetic users and local Chromium. `tests/test_accounts.py` covers hidden defaults, owner-only session controls, password rotation, concurrent reset protection, expiry, bounds, recovery, throttling and credential-free CLI output. `tests/test_accounts_browser.py` covers the default local dashboard, password controls, a delayed old-token response and logging into another account with an unsaved old notebook.
