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
| `GET /api/packs/{id}` | Parsed pack data |
| `GET /api/stats` | Derived streaks, days, freeze allowance and eight weekly minute totals |
| `GET /api/heatmap` | Day/count values for the last 12 calendar weeks |
| `GET /api/search?q=text` | Reverse chronological substring matches |
| `GET /api/account` | Current account and reminder preferences |
| `POST /api/command` | `{argv:[...],pack_text?:"..."}`; same application commands as the CLI |

`/api/command` supports mission lifecycle, config, edit/undo, backfill, split,
verification, and parking. It rejects client-only timer installation and pack
scaffolding. Pack paths sent by a client must include `pack_text`; the server does
not interpret them as arbitrary host file paths. An export returns Markdown to
the client, which chooses where to save it locally.

The node reference is `pack-id:node-id`. Omitting it uses the active mission's
next eligible main node, falling back to its side lane. Manual completion routes
remain explicit, even when a verifier would fail. `done --complete` logs partial
work on verification failure, returning `completed: false` and a reason.
