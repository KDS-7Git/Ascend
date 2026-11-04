# Reach a service through an edge

Route requests through a private edge and prove TLS name and trust behaviour.

Guided practice: about 60 minutes. Independent application: about 120 minutes, split over sessions when needed.

## Before you start

Python 3.11+ for the local proxy; Caddy and OpenSSL for the real TLS extension.

Download /training/devops-service-foundations.zip and extract it into a new folder you choose on your own PC. Open a terminal in the extracted devops-service-foundations folder; commands use that folder unless a step explicitly changes it. Read README.md and shared/README.md. The core tools need Python 3.11+ and no Python packages. Shell examples use Linux/macOS; use a Linux guest or WSL for POSIX commands on Windows. Keep foreground services in separate terminals and stop earlier listeners before reusing a port. Create notes/edge-tls.md from notes-template.md in your editor and keep predictions, exact commands, observed output and explanations there. If that file already exists, append a dated attempt or choose a new name. work/, data/, backups/ and restored/ hold the explicitly named local outputs. These files stay on your computer; opening a challenge does not create or upload them. Use Ascend's notebook or chosen upload control only when you intend to copy evidence into Ascend.

## How it works

The reverse proxy has its own listener and upstream. TLS authenticates a hostname under a trusted CA; trust failure and name mismatch are different. A working process can remain unreachable through an incorrect edge route.

## Guided practice

### Step 1

Start a fresh Relay v1 on port 8000 in Terminal A using the following command. Terminal B will run the edge; Terminal C will run the clients.

### Step 2

```sh
python3 shared/relay.py --port 8000 --data work/edge.sqlite --release v1
```

### Step 3

```sh
python3 shared/edge.py --config configs/route.json --port 9000
```

### Step 4

```sh
curl -i http://127.0.0.1:8000/version
curl -i http://127.0.0.1:9000/version
```

### Step 5

Stop the teaching edge. Run the equivalent Caddy configuration and compare behaviour. Keep Caddy's listener and origin private to this machine.

### Step 6

```sh
caddy validate --config configs/Caddyfile --adapter caddyfile
caddy run --config configs/Caddyfile --adapter caddyfile
```

### Step 7

Stop that Caddy process before the TLS extension. Generate a temporary lab certificate, then run the supplied TLS edge. This certificate is trusted only by the following client invocation.

### Step 8

```sh
mkdir -p work
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -keyout work/key.pem -out work/cert.pem -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost'
caddy run --config configs/Caddyfile.tls --adapter caddyfile
```

### Step 9

```sh
python3 shared/check_service.py --url https://localhost:9443 --ca-file work/cert.pem --expect-release v1
curl --cacert work/cert.pem https://127.0.0.1:9443/version
```

## Independent application

Predict the result before opening the guided solution. If you already know the subject, attempt this application first; the guided practice is available when you need it.

1. Use route-fault.json with the teaching edge, record the 502 and the still-working direct backend, then repair the route in a working copy.

2. For the real TLS edge, show a trusted correct-name success, an untrusted-CA rejection and a wrong-name rejection without -k.

3. Explain what additional DNS/router/public-address conditions would be needed for an Internet deployment; the loopback exercise does not prove those.

## Finish line

Direct and edge observations locate a routing fault, legitimate controls survive the repair, and TLS trust/name negative controls reject as expected. Review the observations and explanation in your local notes before marking done. A required live operation remains incomplete until you perform it in the stated environment. Manual completion records your assessment; local tool output or a saved file does not automatically verify skill.

## Return later

After a suggested 2–7 days, reconstruct the request/state/identity path from memory. Predict one failure from this lesson, then check it against a fresh observation or your retained evidence. Record what changed in your explanation. Spacing is your choice; Ascend does not pretend to verify how long you waited.

[Free technical reference](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
