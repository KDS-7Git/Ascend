# HTTP API

The server publishes its precise OpenAPI schema at `/openapi.json` and interactive
reference at `/docs`. JSON business-validation failures return **400** with a
`detail` string; malformed request schemas return **422**; missing authentication
returns **401**; missing pack resources return **404**; write conflicts return
**409**. Private API responses have `Cache-Control: no-store`.

In `AUTH_MODE=multi`, use `Authorization: Bearer <token>`. The health endpoint and
login are unauthenticated. Accounts are provisioned using `ascend-server user-add`.
There is no public registration endpoint. Passwords use scrypt; tokens are hashed
at rest. Browser tokens are session-scoped, and CLI tokens are stored with mode 0600.

| Route | Contract |
|---|---|
| `GET /api/health` | `{status, auth_mode}` |
| `POST /api/login` | `{username,password}` → `{token}` |
| `GET /api/me?minutes=30` | Mission, next/quick-win node data, current level, streak and today state |
| `GET /api/levels?pack=<id>` | Levels with node states, active days and minutes |
| `POST /api/entries` | `{learned,next_step,node_id?,proof?,minutes?,complete?,force?,mission_id?}` → entry ID, logical day and completion result |
| `GET /api/entries` | Caller-scoped learning entries |
| `POST /api/nodes/{pack:node}/mark` | `{status,note?}`; status is done/skipped/todo |
| `POST /api/packs` | Multipart `file`: UTF-8 TOML, maximum 2 MB; lint and install |
| `GET /api/packs` | Installed pack IDs and review/trust metadata |
| `GET /api/packs/{id}` | Pack metadata and preview nodes |
| `GET /api/stats` | Derived streaks, days, freeze allowance and eight weekly minute totals |
| `GET /api/heatmap` | Day/count values for the last 12 calendar weeks |
| `GET /api/search?q=text` | Reverse chronological substring matches |
| `GET /api/account` | Current account and reminder preferences |
| `POST /api/command` | `{argv:[...],pack_text?:"..."}`; same application commands as the CLI |
| `POST /api/logout` | Revoke the current token |
| `GET /api/push/key` | Configured public VAPID key |
| `POST /api/push/subscriptions` | Browser PushSubscription JSON; user-scoped upsert |
| `DELETE /api/push/subscriptions` | `{endpoint}`; remove caller's subscription |
| `POST /api/telegram/webhook` | Telegram Update; requires the Telegram webhook secret header |
| `GET /api/public/{username}/streak` | Minimal opt-in streak data; 404 otherwise |
| `GET /api/public/{username}/badge.svg` | Opt-in SVG badge |

`/api/command` supports mission lifecycle, config, edit/undo, backfill, split,
verification, and parking. It rejects client-only timer installation and pack
scaffolding. Pack paths sent by a client must include `pack_text`; the server does
not interpret them as arbitrary host file paths. An export returns Markdown to
the client, which chooses where to save it locally.

The node reference is `pack-id:node-id`. Omitting it uses the active mission's
next eligible main node, falling back to its side lane. Manual completion routes
remain explicit, even when a verifier would fail. `done --complete` logs partial
work on verification failure, returning `completed: false` and a reason.

Web overview, level and pack listings return preview nodes. Full instructions,
downloads, hints, finish lines and verifier internals are omitted. Learning
resource links, labels and notes remain available before Start.
`GET /api/challenges/{pack-id:node-id}` returns `details_available: true` only
for an existing caller-owned session or historical completion. Ended attempts
retain review access; `has_attempt` lets the UI offer Review attempt without
starting a new timer. Remote `today` and `levels` follow the preview contract.
Public source pack exports remain authoring data.


Playground is independent of mission/node routes:

| Route | Contract |
|---|---|
| `GET /api/playground` | Catalog; filters: domain, kind, minutes, topic, difficulty, environment, progress, format, search, bookmarked |
| `GET /api/playground/recommendations?minutes=10` | Ready activities, review schedule and explicit alternatives; accepts catalog filters and comma-separated exclude IDs |
| `GET /api/playground/history` | Caller-owned saved work and final results |
| `GET /api/playground/insights` | Caller-scoped usage observations for 14 days |
| `POST /api/playground/selection` | `{data:{filters...}}`; observe a selection once per user/day/filter |
| `GET /api/playground/activities/{id}` | Public brief, abilities, separate preparation and saved runs |
| `POST /api/playground/activities/{id}/start` | `{deliberate?:false,end_scored?:false}` → public run |
| `POST /api/playground/activities/{id}/bookmark?enabled=true` | Add/remove bookmark |
| `GET /api/playground/runs/{run}` | Same fixture, work, assistance and reveal state |
| `POST /api/playground/runs/{run}/{action}` | resume, save, submit, log, experiment, copy, repair, hint, end, reveal, tour, feedback, returned |
| `GET /api/nodes/{reference}/checkpoints` | Authored parts, saved states and full parent estimate |
| `POST /api/nodes/{reference}/checkpoints/{id}` | `{learned,minutes?}`; save a partial learning entry without completing or retiming the parent |

Save/submit/experiment use `{data:{...}}`; save accepts `pause` (default true)
for worked examples and free workspaces. Assessed challenges ignore `pause`:
their timer runs from the original start until completion or an explicit end,
including time away. History returns individual runs; the browser groups them
by `activity_id` at `#attempts/ACTIVITY_ID` without discarding earlier versions.
Log uses `{learned,next_step?,minutes?}`; an example submission requires learned.
An omitted next_step uses a general return action. Copy accepts reset/blank/fault flags. Repair accepts a rule. Resume
and copy accept `end_scored` for the explicit scored-session switch. A saved run
must be resumed before assessment submission. A full solution is available only
after passing or explicitly ending a run. Private rubric data is never returned
in catalog, detail or unfinished-run responses.

`/api/command` also supports `practice 10` and all `playground` commands. Activity
logs use an explicit run reference with no mission association. Final results and
rewards are atomic and idempotent. XP in Stats is split into track/practice/challenge
contributions. See the canonical user/developer guides for caps and readiness rules.

Tour uses `{step:0,status:"active"}` (zero-based step; status may also be `finished`
or `skipped`), for worked examples only. Feedback accepts a `data` object with
`working_minutes`, `setup_minutes`, `difficulty` (too-easy/about-right/too-hard),
`clarity` (clear/unclear), `repetition` (fresh/welcome-review/unwanted-repeat),
`environment_issue` and `note`. It never affects XP or readiness. Three completed,
clear, problem-free reports can raise a personal time allowance above the authored
estimate. `returned` records an explicit return-to-track action. GET selection
routes remain read-only. CLI equivalents include `playground tour`,
`playground feedback`, `playground insights`, and `checkpoint list/log`.

Local-lab references and submissions use separate routes:

| Route | Contract |
|---|---|
| `GET /api/lab-catalog` | Shared references/recipes; filters: track, level, location, search. Performs no downloads. |
| `GET /api/lab-catalog/{id}` | Source pins, license, platform measurements, lifecycle/review gates and evidence scope. Pack detail also includes `lab_references`. |
| `GET /api/lab-attempts` | Account-owned history; expired foreground reservations are released. |
| `POST /api/lab-attempts` | `{recipe_id,offline?:false,case_key?:integer}` → attempt, nonce, recipe/checker/fixture versions and optional assignment. `case_key` (0–65535) is accepted only for an offline policy import. |
| `GET /api/lab-attempts/{id}` | Owned attempt and result; never returns its nonce or nonce hash. |
| `POST /api/lab-attempts/{id}/ready` | `{nonce}`; begins an online attempt clock after local readiness. |
| `POST /api/lab-attempts/{id}/abandon` | `{nonce}`; releases the reservation. |
| `POST /api/lab-attempts/{id}/submit` | `{nonce,recipe_version,checker_version,fixture_id,answers? or report? or submission?}`; the recipe fixes the permitted evidence shape. |

All POST bodies under `/api/lab-attempts` are bounded to 1 MiB, including streamed
uploads. Unknown fields, cross-account use, wrong versions/cases and replay are
rejected. `/api/command` rejects every `local-lab` command even in single-user
mode; those commands execute on the PC through the companion CLI.

`linux-audit-discovery` accepts its explicit answer object and uses a server-owned
rubric. VAmPI/WrongSecrets accept the exact local checkset; upstream imports use
their recipe's bounded report contract. Specialist imports include pinned
environment identifiers and are labeled manual observations.

Prepared learner-local workspaces submit `report: {evidence: ...}` using the
same attempt route. The package carries `schema_version: "local-artifacts-v1"`,
the recipe/source revision, exact environment fields and named artifacts with
canonical SHA-256 hashes and bounded JSON content. Individual observations are
limited to 64 KiB; the complete request still has the 1 MiB limit. The server
derives the named checks again, including required negative controls, and returns
**Local evidence reviewed** with local authority. Missing observations remain
unsupported, altered hashes and unexpected fields are rejected, and local
artifacts do not authenticate the earlier environment. `prepare`, `observe` and
`capture` are companion CLI operations; the server accepts their evidence only.

`bgp-export-policy` accepts only `submission: {files: {"policy.json": <object>}}`,
at most 64 KiB and 32 declarative IPv4 rules. The server issues the online case
and runs its fixed model checker in a temporary Linux worker. A fresh offline
import can supply its bounded case key; the server derives the case and tests.
The receipt includes a canonical JSON submission hash and says **Submission
tested (policy model)**. It does not prove router behavior or prior local actions.
Worker failures leave the attempt available for retry. No uploaded executable,
archive or caller-selected server path is accepted. Results and hashes persist;
the policy worker's temporary files are removed.

Local-lab records have `satisfies_track_evidence: false` and award zero XP.
Offline receipts have no claimed server start time. Existing track receipts,
reward rules and session clocks retain their semantics.

### Browser labs on a separate server

| Endpoint | Contract |
| --- | --- |
| `GET /api/hosted-labs/capabilities` | Configured status, enabled recipes and capacity. |
| `GET /api/hosted-labs/runs` | Caller-scoped runs and latest asynchronous job. |
| `POST /api/hosted-labs/runs` | `{recipe_id}` queues a reviewed launch; poll runs for completion. |
| `POST /api/hosted-labs/runs/{id}/{action}` | check, stop, resume, finish, destroy, save, http or router. Strict bounded action schema; caller scope is server-derived. |
| `GET /api/hosted-labs/runs/{id}/files?name=...` | Selected input/work files only, at most 256 KiB. |

POST wire bodies are limited to 1 MiB. HTTP requests select a fixed target and
relative path; redirects and CONNECT are refused. Router commands match a fixed
exercise allowlist on the learner router. Queued/running operations have retained
job IDs; an interrupted runner marks the job failed and reconciles inventory.
A disconnected runner returns 503. Runtime cleanup failures keep the owned run
retryable. See [server deployment](design/server-lab-runner.md).
