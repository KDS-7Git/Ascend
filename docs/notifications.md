# Notifications and public streaks

Reminders are opt-in on the server. Configure them in **More → Reminders** or
with `ascend config nudge-enabled true`. First test the chosen channel. The
server owns the log and schedule; clients do not mirror the database.

## ntfy

The default server channel is ntfy. Subscribe to a long private topic using the
ntfy Android app, set `ascend config ntfy-topic <topic>`, and choose
`ascend config nudge-channel ntfy`. `NTFY_SERVER` may point to your own instance;
`NTFY_TOKEN` is read only from the environment. Public hosted topics are known
by their names, so use a random topic and do not put secrets in reminders.

## Telegram and inline quick actions

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the server environment, then
select `ascend config nudge-channel telegram`. Credentials are never stored in
SQLite. For multi-user servers, the administrator maps each account using
`TELEGRAM_CHAT_ID_<numeric-user-id>`. Only configured private chats are accepted.

Reminders include **Log a step** and **Log quick win** buttons. Tapping a button
starts a twenty-minute conversation: what you learned (minimum 20 characters),
then your next step. Both fields go through the shared secret guard and entry
validation. The result is a partial learning entry, not an automatic node tick.
`/cancel` abandons the conversation. Telegram update IDs prevent duplicate logs
when webhook deliveries are retried.

For buttons to work, expose the server through HTTPS and register
`https://your-domain/api/telegram/webhook` with Telegram's `setWebhook` method,
including a random `secret_token` matching the server's
`TELEGRAM_WEBHOOK_SECRET`. See [Telegram's official Bot API](https://core.telegram.org/bots/api#setwebhook).
`ASCEND_PUBLIC_URL` supplies the optional Open Ascend button. Missing bot/chat
credentials fall back to desktop with a warning recorded once; a headless
server reports the unavailable desktop transport explicitly.

## Web Push: no separate Android app

Install the optional dependency and generate a persistent VAPID key pair:

```sh
pip install '.[server,push]'
ascend-server push-keys --out /your/private/ascend/vapid.pem
```

The command writes the private key with mode 0600 and prints only the public key.
Set `VAPID_PRIVATE_KEY` to the private file's path and `VAPID_SUBJECT` to a
`mailto:you@example.com` contact or an HTTPS contact URL. The Docker image includes
the Push extra; generate the key as the container user under `/data/` so it
persists in the volume. Key generation refuses to overwrite an existing file.

Serve the PWA over HTTPS. In More, choose **Enable browser notifications**, grant
permission, enable reminders, and send a test. Subscriptions belong to the logged-in
account. The service worker displays encrypted push payloads and opens the app
when tapped. Disable on this browser removes only that browser's subscription.

The server validates HTTPS push-service endpoints and subscription keys, uses
pywebpush for standard encryption and VAPID authentication, and removes expired
404/410 subscriptions. Common Chrome, Firefox, and Apple provider hosts are
accepted. An administrator can add exact providers with `PUSH_ALLOWED_HOSTS`.

Automated verification covers actual payload encryption and VAPID headers while
mocking the final HTTP transport. It does **not** establish real Android delivery:
that needs your own domain, keys, notification permission, and subscribed device.

## Opt-in public streak and badge

`ascend config public-streak true` (or More → Share my streak publicly) exposes:

- `/api/public/<username>/streak`: current and best streak plus today's logged flag.
- `/api/public/<username>/badge.svg`: an embeddable SVG badge.

These routes return 404 until enabled. They never include entries, proof, private
packs, mission names, or learning notes. Set the option back to false to withdraw
access. The implicit standalone/single-server username is `local`.
