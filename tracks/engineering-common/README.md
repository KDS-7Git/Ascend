# Shared Relay tools

These inspectable Python 3.11+ tools use the standard library. Run them on your own PC or disposable Linux guest. They do not provision a cloud account or connect to Ascend's runner.

From an extracted engineering track folder:

```sh
python3 shared/relay.py --host 127.0.0.1 --port 8000 --data data/relay.sqlite --release v1
```

The startup line names the actual address, port and database path. Keep that terminal open. In a second terminal, in the same folder:

```sh
python3 shared/check_service.py --url http://127.0.0.1:8000 --expect-release v1 --write
```

The explicit `--write` option retains one synthetic update and verifies idempotent replay plus rejection of a conflicting write. Without it, checks read the service. A local observation report is not an automatic Ascend grade. Use your task's Check evidence/Log progress controls only after completing its actual finish line.

`/health` is liveness; `/ready` checks the state store and optional readiness gate; `/version` reports release identity; `/api/updates` reads and writes synthetic updates; `/metrics` exposes bounded-cardinality counters; `/work` waits for the configured `--delay-ms` (0–1000). `--workers` caps accepted request-handler concurrency (1–64); excess accepted sockets receive 503. This is a teaching server, not a hardened production HTTP server or a requests-per-second guarantee.

For a read-only replica, add `--read-only`. For deliberate readiness changes, use `--ready-file state/ready.txt`; only a file containing `ready` opens the gate. For protected writes, use `--token-file secrets/write-token.txt` and pass the same file to the checker. The service rereads the token for every write, enabling a rotation exercise. Tokens and database records stay on the learner's machine. Use only synthetic values.

Use `--ca-file path/to/ca.pem` with the checker for a private-CA HTTPS edge. Verification stays enabled; the trust scope is this invocation. `--timeout` is bounded to 0.2–10 seconds per request.

Back up a running database consistently, then restore to a **new** path:

```sh
python3 shared/backup.py create --source data/relay.sqlite --destination backups/relay-first.sqlite
python3 shared/backup.py restore --source backups/relay-first.sqlite --destination restored/relay.sqlite
python3 shared/backup.py inspect --source restored/relay.sqlite
```

Existing destination files are preserved. The SQLite backup API includes a consistent database snapshot; copying a live `.sqlite` file while ignoring its WAL is not an equivalent procedure. Stop the old service and start one using the restored path to verify the restore. The output records a count and logical-record hash; retain the original backup. A backup on the same physical disk does not protect against losing that disk.

Run `python3 shared/selfcheck.py` to exercise the supplied application and tool controls on temporary loopback services. Later track instructions add real systemd, container, SSH, CI, IaC and Kubernetes operations with their own requirements.

The eight selfchecks cover real endpoint/replay controls, readiness and token rotation, read-only restart/persistence, consistent snapshot/restore, artifact tampering, proxy routing failure/recovery, bounded admission and recovery, and measurement/target limits. They finish in a few seconds and delete their temporary state. Their success validates these reference tools, not the learner's completion of the independent challenges.

## Select and activate a release

```sh
python3 shared/release.py build --source shared/relay.py --out work/releases/v1 --release v1 --revision local-reviewed
python3 shared/release.py verify --artifact work/releases/v1
python3 shared/release.py select --artifact work/releases/v1 --state work/current.json
python3 shared/release.py serve --state work/current.json -- --port 8000 --data work/runtime.sqlite
```

The manifest identifies the entrypoint content and supplied revision. Build refuses an existing artifact directory. Verification rejects modified bytes and unexpected files. Selection atomically replaces a small local pointer under an exclusive lock; it does not alter running code. Restart the selected service deliberately and check `/version` to observe activation. Configuration and state stay outside the artifact. A digest does not authenticate who produced the artifact. These commands run locally reviewed code on the learner's chosen machine; never use them as an uploaded-code runner on the Ascend server.

## Inspect an edge and a small workload

The foundations bundle supplies a JSON route and equivalent Caddy configurations:

```sh
python3 shared/edge.py --config configs/route.json --port 9000
```

The teaching edge is loopback-only and GET-only. It rereads its two-field route file for each request, bounds the upstream response and timeout, and returns 502 for an invalid or unavailable origin. Compare a direct origin observation with the edge response to locate the fault. Use the separate Caddy lesson for TLS and a full reverse proxy.

The bounded load helper runs at most 16 closed-model clients and 200 total requests. Each client waits for one request to finish before starting another; it cannot prove a fixed arrival-rate capacity claim.

```sh
python3 shared/probe_load.py --url http://127.0.0.1:8000/work --clients 4 --requests 24 --output notes/load.csv
```

Record the printed `window_seconds` and supply that actual number to the analyzer:

```sh
python3 shared/analyze.py notes/load.csv --window-seconds YOUR_OBSERVED_SECONDS
```

Use a new output path for a new run. A non-loopback load target requires `--allow-owned-remote-target` and must be your explicitly owned test service. The default stays local. The analyzer counts every attempted row, including connection failures and admission rejections, and reports successful throughput alongside both all-response and successful-response p95. It exits with status 1 when the selected error or latency objective is missed; this is often the intended observation in the overload lesson. The measured window and workload model limit every conclusion.
