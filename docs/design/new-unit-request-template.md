# Request template: draft a new hackstreak pack

Copy everything below the line into a NEW chat with Claude (it does not remember earlier chats, so this carries everything).
Fill in the five fields marked <<...>>. Keep the rest as it is.

---

Draft a hackstreak pack (a learning roadmap) for me. Reply with ONLY the TOML file, nothing else.

## My request
- Topic / unit: <<e.g. "Networking: how packets really move, with Beej's guide and Wireshark">>
- Kind: <<"proficiency" (I want to get genuinely good at this subject, give me 8-15 levels) OR "project" (one concrete
  build with a finish line, 3-6 levels) -- pick one>>
- What I already know or have finished: <<e.g. "Bandit 0-12, basic C, Python, ssh">>
- Time reality: <<e.g. "10-30 min on deadline days, 1-2 h on lab nights, 4+ h on free half-days">>
- Hardware / tools: <<e.g. "Ubuntu 24.04 + Windows 11 dual boot, RTX 4060 8 GB, 16 GB RAM, Raspberry Pi 5 8 GB, LAN cable">>
- What real proficiency/finished should look like: <<e.g. "I can capture and explain a TCP handshake, write a raw-socket
  tool, and debug a real connectivity issue without googling the basics">>

## About me (stable, keep as is)
Wide interests (software dev, web, mobile, game dev, OS, networks, low-level, cybersecurity) and I get overwhelmed and lose the
thread when a plan is open-ended. I distrust AI-generated learning content. I only want real, free, well-known resources, and I
learn best from small puzzles with a real check. I am a CSE student at an IIT with heavy academic load. I only attack machines I own.

## Format rules (the hackstreak pack format)
- Sections: `[pack]` (id, title, kind = "proficiency" or "project", version = 1, source = "ai-draft", reviewed = false),
  `[vars]`, `[[level]]`, `[[node]]`.
- Levels, `kind = "proficiency"`: 8-15 on the `main` lane, each a real sub-skill with 4-8 nodes (like a Duolingo unit),
  and each level ends with one node marked `milestone = true` (size M or L) that is a harder, integrative task --
  something built or explained from scratch, not a repeat of the level's small steps. That milestone is the actual
  proficiency check; do not skip it.
- Levels, `kind = "project"`: 3-6 on the `main` lane total, same milestone rule, smaller overall.
- Either kind: optionally ONE `side` lane level of S-sized quick wins for busy days. Each `[[level]]` has id, title,
  lane ("main" or "side").
- Each `[[node]]` has: level, id (kebab-case, unique, never changes), title, size, needs (list of node ids, may be empty),
  done_when, resource, optionally `milestone = true`, and optionally verify.
- size: "S" = up to 30 min, "M" = 1-2 h, "L" = 3 h or more. Mix sizes so busy days have an S option.
- done_when: ONE concrete, checkable sentence. Prefer an artifact on my disk (a file, a scan, a script, a short writeup).
  Never "understand X" or "read chapter Y" alone; pair reading with something I produce.
- resource: a real, well-known URL. If you are not sure a URL exists, write `resource = "TODO"` instead of guessing.
  Do NOT write lesson content or explanations, only the plan.
- verify (optional): `{ type = "manual" }` (default), `{ type = "file", path = "...", min_bytes = N }`, or
  `{ type = "command", cmd = "..." }` (exit code 0 = pass; harmless read-only commands only, no sudo).
- Use `series = { from = A, to = B }` for numbered material, with `{n}` and `{next}` in title/done_when.
- Use `[vars]` for values I will edit (IPs, usernames, folders) and refer to them as `{name}`.
- Never ask me to store passwords, flags, or tokens.
- The first node of the first level must be startable tonight in 30 minutes or less.

## Tiny example of the style
```toml
[pack]
id = "example"
title = "Example"
version = 1
source = "ai-draft"
reviewed = false

[[level]]
id = "basics"
title = "Basics"
lane = "main"

[[node]]
level = "basics"
id = "first-capture"
title = "Capture my first packets"
size = "S"
needs = []
done_when = "a 30-second capture saved at ~/hack/pcaps/first.pcapng that contains at least one DNS query"
resource = "https://www.wireshark.org/docs/"
verify = { type = "file", path = "~/hack/pcaps/first.pcapng", min_bytes = 1000 }
```

---

After you get the reply: save it as `packs/<id>.toml`, then run
`ascend pack lint packs/<id>.toml`, `ascend pack check-links packs/<id>.toml`, read every `done_when`, then
`ascend review <id>` and `ascend pack install <id>`. (The CLI binary is `ascend`, not `hack` — the earlier drafts of
this project used `hack` before the public rename; use `ascend` for every command.)
