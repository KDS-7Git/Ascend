# Reproduce a small local infrastructure lab

This is the executed reference slice for the [Infrastructure & Internet Operations domain](../../infrastructure-internet-domain-design.md). It uses **real Caddy** and two small Python HTTP fixtures to demonstrate routing, TLS, readiness, admission limits and recovery. It is also a practical experiment learners can rerun and change.

The [default result](evidence.json) and [one-slot variant](evidence-one-slot.json) record ten checks each, with source hashes, tool identity, parameters, observed controls and cleanup. Their scope is one host and loopback networking. They do not establish a public deployment, a real VPN/tunnel, mail deliverability, VM administration, physical-device performance or the teaching effectiveness of the full domain.

## Requirements and run

Use Python 3.10+, OpenSSL and a Caddy binary. The recorded run used Linux amd64, Python 3.12.3 and **Caddy v2.11.7**. Other platform/version combinations need a separate run before being described as tested.

Obtain Caddy from its [official release](https://github.com/caddyserver/caddy/releases/tag/v2.11.7), choosing your actual OS/architecture. No executable is vendored or downloaded automatically by this lab. [Tool provenance](tool-provenance.json) records the original Linux archive's SHA-256 from the release API and its independently matched SHA-512 entry in the release checksum file. This verifies those published digests; the release signature was not independently verified.

From the repository root, run:

```bash
python3 docs/design/labs/local-to-internet/lab.py \
  --caddy /path/to/caddy \
  --output /tmp/ascend-http-proof-default.json
```

If Caddy is already on PATH, omit `--caddy`. The repository's `.venv/bin/python` can replace `python3`. The process prints each passing observation and the exact saved report path. Without `--output`, it prints the JSON report and creates no retained result file.

The lab creates only its own temporary application processes, HTTP/TLS listeners, certificate, private key and Caddy configuration. Caddy's admin interface, automatic certificate issuance and config persistence are disabled. HTTP and HTTPS explicitly bind to `127.0.0.1`; the adapted configuration is checked, and Linux runs also inspect the child process's actual listening sockets. The lab uses a certificate trusted only by its own test client, then removes its temporary files and shuts down its owned services. No machine trust-store change or public tunnel is performed.

## Predict, observe, change

Before running, predict these results:

1. Eight sequential requests through an explicit round-robin policy should reach each healthy backend four times.
2. An intentionally non-listening upstream should produce a 502 while the valid route still works.
3. A trusted certificate with the correct name should work; an untrusted CA and a wrong name should be rejected by the client.
4. After app B loses readiness, new balanced requests should reach A while an already active B request can complete.
5. With two admitted-work slots and twelve concurrent clients held at the admission point, useful work should remain bounded and excess requests should receive 503; later work should recover.

Then change **only the work-slot count**, keeping the same burst:

```bash
python3 docs/design/labs/local-to-internet/lab.py \
  --caddy /path/to/caddy \
  --workers 1 \
  --output /tmp/ascend-http-proof-one-slot.json
```

Compare the `bounded-work-and-overload-rejection` evidence in both files. Explain why a lower admission limit changes accepted/rejected work but does not by itself measure a machine's maximum useful throughput. `--burst` is capped at 16 clients and `--work-ms` controls a short simulated dependency delay. No CPU or storage stress test is performed.

Read [lab.py](lab.py), especially the Caddyfile and its `/ready` behaviour. In a separate copy, try a different explicit balancing policy or readiness endpoint and predict which assertion should fail. Restore the working version and reproduce the pass. A failed assertion is evidence of that experiment; suppressing it does not repair the system.

For the full course, the follow-on independent task must provide a fresh fixture and require the learner to configure and diagnose it. Running this reference script alone does not demonstrate independent mastery.

## Exact evidence boundaries

The in-flight experiment routes one held request through an explicit `/slow-b` path, then observes that the balanced route excludes B while that operation is still active. It proves those two controls; `/slow-b` itself deliberately bypasses readiness balancing, so this is not a claim that every path to B is drained.

The semaphore limits **application work**, not all accepted TCP connections, HTTP threads or operating-system memory. The burst includes an artificial bounded wait so overload can be observed with few requests. Open-arrival load, realistic CPU work, stateful writes, generator saturation, p95 capacity and resource feasibility require the later track's separate experiments.

Any recorded Caddy memory is a process observation on the recorded host. It excludes Python, OS, VM overhead, image/build/transient work and other services; it is not a minimum-RAM recommendation or proof that a shared host can serve a stated number of learners.

Readiness checks may close a connection after reading its status. Such peer disconnects are counted in the report rather than shown as unhandled fixture errors. The proof still requires the tested client responses to arrive and satisfy their assertions.

The report is a reproducible development artifact, not an Ascend verification receipt. A learner can edit a local JSON file; stronger track evidence requires the explicitly designed review or trusted checking boundary.
