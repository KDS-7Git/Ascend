# Disposable browser labs: comparison and implementation boundary

Reviewed on 2026-11-02. This is public documentation and source review, not a
security audit of these services or a claim about their private infrastructure.
Ascend's preview/workspace disclosure is implemented. Per-attempt containers and
an embedded shell are **not implemented or enabled** by that change. The existing
`docker/labs.compose.yml` profiles remain administrator-managed external labs.

## What established platforms actually document

| Platform | Documented approach | Useful lesson for Ascend | Limit of the evidence |
| --- | --- | --- | --- |
| [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) | SSH accounts and successive levels. Its [rules](https://overthewire.org/rules/) require hard-to-guess temporary paths and cleanup. | Clear objectives, identified connection details and explicit workspace hygiene. | These pages do not establish disposable containers per attempt or describe host hardening. Do not represent Bandit as that architecture. |
| [pwn.college](https://github.com/pwncollege/dojo/blob/ee1c6e2653d8aa8301b6190a4f5dafb829471418/docs/architecture.md) | Per-user challenge workspaces with browser/SSH access, controlled lifecycle and optional separate workspace nodes. | Separate workspace infrastructure from the web application; authenticate access and retain the same environment across navigation. | The pinned [container creation code](https://github.com/pwncollege/dojo/blob/ee1c6e2653d8aa8301b6190a4f5dafb829471418/site/dojo/api/v1/docker.py) uses Kata for challenges marked privileged and runc otherwise. It also uses capabilities/mounts tailored to its deployment; these are not an Ascend configuration template. |
| [TryHackMe AttackBox](https://help.tryhackme.com/en/articles/6721845-the-attackbox-explained) | Browser-accessible Ubuntu VM, alongside task target machines, with loading, time limits and explicit termination. | Show preparation status, start learning time when ready, and offer an obvious return path. | Public help describes the experience, not the complete hypervisor or network isolation design. |
| [CTFd Application Target](https://docs.ctfd.io/docs/custom-challenges/application-target) | Per-account deployments, a supported Compose subset, redeployment and resource settings. | Allowlisted lab definitions and bounded instances rather than arbitrary user-supplied container options. | The docs say an instance is accessible to anyone who knows its URL/hostname. Ascend must check account ownership; an obscure address is insufficient. This feature is documented as hosted/Enterprise and beta. |

Additional sources inspected:

- [TryHackMe: starting a machine](https://help.tryhackme.com/en/articles/7977454-how-to-starting-your-first-tryhackme-machine)
  distinguishes starting, waiting for readiness, expiry and termination.
- [TryHackMe: disabling AttackBox internet](https://help.tryhackme.com/en/articles/10449553-stop-internet-access-for-students-on-the-attackbox)
  demonstrates that outbound access needs an explicit policy; a training desktop
  can otherwise bypass an institution's network restrictions.
- [CTFd network service containers](https://docs.ctfd.io/tutorials/challenges/network-service-challenge-containers)
  demonstrates service wrapping and connection timeouts. It is not evidence that
  exposing an arbitrary shell is safe.
- [xterm.js security guidance](https://xtermjs.org/docs/guides/security/) treats the
  renderer, transport and backend as separate concerns. Use text-safe rendering,
  reviewed local assets, explicit authentication and WebSocket Origin checks.
  A terminal emulator does not sandbox the process behind it.
- [gVisor Docker setup](https://gvisor.dev/docs/user_guide/quick_start/docker/)
  requires an installed/registered runtime; specifying a label is not isolation.
- [Docker rootless prerequisites](https://docs.docker.com/engine/security/rootless/)
  include UID/GID mapping helpers. Rootless operation reduces daemon privileges
  but is not a separate guest-kernel boundary.

pwn.college source observations refer to commit
`ee1c6e2653d8aa8301b6190a4f5dafb829471418`, not an assumed current deployment.
No platform's credentials, challenge answers or copyrighted lab materials were
copied into Ascend.

## Architecture selected for the browser-terminal feature

The web application authenticates the learner and owns attempt/timer state. A
separate runner provisions approved lab definitions. Its control channel must
not be reachable from a learner container or exposed as an arbitrary Docker API.
The application container must not gain a Docker socket mount.

Start with a small, network-independent HTTP/Python lab. A reviewed image includes
the required tools and fixtures. The learner receives a non-root shell and a
temporary writable workspace; the image filesystem is read-only. Do not promise
that every track can run this way. Windows/AD, kernel exploitation, nested
container orchestration, device access and physical radio tasks need different
capability classes and an appropriate VM or external lab.

Required controls before enabling a general shell:

- Require an explicitly configured gVisor runtime for supported user-space labs,
  or a dedicated VM/Kata boundary for labs that need a guest kernel. Refuse startup
  when the required runtime is unavailable. Do not fall back to runc or a host
  subprocess shell.
- Resolve immutable images from an administrator-controlled allowlist. Learners
  cannot select images, mounts, runtimes, capabilities, devices, networks or host
  paths. Pack installation alone cannot grant runner privileges.
- No host bind mounts, Docker socket, app database, credentials, host namespaces,
  privileged mode or host devices. Drop capabilities; apply no-new-privileges,
  runtime-appropriate seccomp, and CPU, memory, PIDs, workspace, output and lifetime
  limits. Keep network disabled for standalone labs. Any multi-service lab gets a
  per-attempt network with explicit destinations and blocked host/metadata access.
- Authenticate the terminal connection, validate its Origin, and authorize the
  current account against the attempt on every connection. Tokens must not appear
  in URL query strings or terminal logs. Revoke terminal access on logout/end.
- Treat output as untrusted terminal data, never HTML or a script. Bound input,
  output, scrollback and reconnection buffers. Avoid automatic clipboard writes,
  external URL opening and remote CDN scripts.

These layers reduce escape and cross-tenant risk; none supports an absolute
escape-proof claim. Validate the configured boundary and supported challenge
class before exposing it to learners.

## Start, reconnect, save and teardown

1. Preview the short objective, duration, required setup and labeled learning
   resources that learners can consult without starting the timer. No task files,
   detailed commands, hints or solution criteria appear in the preview.
2. Start reserves an attempt idempotently and shows provisioning progress. Enforce
   one active attempt and bounded capacity on the server, including concurrent
   requests. Failed provisioning must not start a timer or reveal a working shell.
3. After readiness checks pass, record the server start time and reveal the full
   task and embedded terminal. Browser reload reconnects to this same instance
   and continuously running timer. There is no pause.
4. Extract only a fixed, size-bounded report through a trusted collector. Reject
   symlinks, special files, path traversal, oversized output and malformed data.
   Store it under an application-controlled attempt key, not a path from terminal
   output or a learner-edited pack. File presence still does not grade reasoning.
5. On complete/end, save available evidence, revoke terminal access and delete
   the instance and its writable storage. A failed save needs an explicit result;
   it must not be reported as successful completion. Saved attempt instructions
   and validated reports remain available for review.
6. Enforce a hard runner deadline and reconcile orphaned instances after crashes.
   The timer target and maximum infrastructure lifetime are distinct: existing
   Ascend targets allow overtime. Communicate an actual hard limit before Start.
   Cleanup must work even if the browser disconnects or the web process dies.

Acceptance must include isolation between two learners, rejected cross-origin and
unauthenticated connections, forbidden host/network access, symlink/large-report
rejection, limits under resource exhaustion, concurrent starts, reload without
timer reset, and teardown after end, expiry and process crashes. Mock runner tests
alone cannot establish isolation on a deployed host.

## This workstation's current blocker

The inspected Docker 29.9.2 daemon advertises only runc/io.containerd.runc.v2. No
gVisor/runsc or Kata runtime is installed. Rootless startup fails because the
`newuidmap` helper is missing, and unprivileged user namespaces are restricted.
Passwordless sudo is unavailable. KVM/QEMU are present, but no isolated runner VM
has been provisioned or validated; roughly 5 GB free disk also constrains images.

Enabling the terminal therefore requires an administrator-prepared isolated
runtime or runner VM, followed by implementation and the deployment acceptance
checks above. The current change deliberately does not offer a host shell or
claim ordinary Docker is an equivalent substitute. No host security setting was
weakened and no learner container was launched for this research.
