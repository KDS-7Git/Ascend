# Deployment

Start locally with `pip install '.[server]'` and `ascend-server`. The default bind
is `127.0.0.1:8420`. To serve your LAN, bind the machine's specific LAN address.
`--host 0.0.0.0` is explicit and prints a reminder to use a TLS reverse proxy
beyond your trusted LAN. Multi-user deployments are for administrator-provisioned
accounts, not anonymous public signup.

```sh
ascend-server user-add alice --timezone Asia/Kolkata
AUTH_MODE=multi ascend-server
```

Every account needs an IANA timezone. Existing standalone data remains with the
implicit `local` account (ID 1). In multi-user mode that account has no password
and cannot log in. Create real accounts for separate users; switching auth mode
does not transfer the local profile's data into a newly created account.

## Docker: Linux PC, VPS, or Raspberry Pi

```sh
docker compose -f docker/docker-compose.yml up -d --build
```

The Python slim base supports amd64 and arm64. The image uses UID 10001 and a
named persistent `/data` volume. Compose maps the service to loopback; put Caddy
or another TLS reverse proxy in front of it. A minimal Caddy configuration is:

```text
ascend.example.com {
    reverse_proxy 127.0.0.1:8420
}
```

Replace the domain and configure DNS before deployment. Android PWA installation
and Web Push require a secure origin. Proxy requests preserve their original
host so the server can validate same-origin browser writes.

If container builds cannot reach PyPI, prepare wheels on the host:

```sh
python -m pip wheel --no-build-isolation --wheel-dir docker/wheelhouse '.[server]' setuptools wheel
docker build -f docker/Dockerfile -t ascend:local .
python scripts/container_smoke.py ascend:local
```

The Dockerfile detects the ignored wheel cache through a build-only mount. Wheels
are not copied into the runtime image or committed. Normal builds download their
dependencies. Actual arm64 execution still needs verification on arm64 hardware.

## Reminders

Set ntfy as the channel, choose a long private topic, subscribe in the Android
ntfy app, send a test, and enable reminders. Environment `NTFY_SERVER` defaults to
`https://ntfy.sh`; optional `NTFY_TOKEN` stays in the environment. Each account can
store a separate topic. Server scheduling checks every thirty seconds and uses
the user's logical day and mission override. It sends at most two successful
scheduled reminders per day and stops after logging. Test sends are explicit and
do not consume daily schedule slots. A second reminder occurs two hours after
the first; schedules close to rollover may have only one reminder that day.

## Trust and backups

Multi-user deployments restrict command, plugin, Git, and HTTP verifiers by
default. `ASCEND_ALLOW_CODE=1` is an administrator opt-in to host-code execution
after each user's explicit trust; enable it only for users you trust with host
permissions. Restricted file checks use `/data/artifacts/<user-id>/`.

Back up SQLite using its backup API rather than copying a live WAL database:

```sh
python -c "import sqlite3; s=sqlite3.connect('/data/ascend.db'); d=sqlite3.connect('/backup/ascend.db'); s.backup(d); d.close(); s.close()"
```

Also back up private packs and plugin files. Test restoring into a separate
`ASCEND_HOME`. Migrations run on startup in numbered transactions. Newer schemas
should not be opened with an older application release.
