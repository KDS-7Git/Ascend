# Pack format

Packs are UTF-8 TOML parsed by Python 3.11+ `tomllib`. See
[`packs/community/`](../packs/community/) for complete examples in cyber, Python,
and 3D art. The examples are drafts for human review, not generated lesson content.

```toml
[pack]
id = "tiny-tool"
title = "Build a tiny file tool"
kind = "project"
version = 1
source = "human"
reviewed = false

[vars]
work_dir = "~/learning"

[[level]]
id = "first"
title = "A working example"
lane = "main"
gate = true

[[node]]
id = "example"
level = "first"
title = "Save a working example"
size = "S"
minutes = 20
needs = []
done_when = "A working example saved with an explanation in my own words"
preview = "Build a tool for organizing a small set of files."
requirements = "Python 3 and a text editor."
brief = "Build a small tool that solves one annoying file-management problem."
steps = ["Choose a tiny input.", "Run the tool and compare its output with your prediction."]
hints = ["Start with one file before handling a whole directory."]
resource = "https://docs.python.org/3/tutorial/"
verify = {type = "file", path = "{work_dir}/example.py", min_bytes = 20}
```

Required pack fields: kebab-case `id`, `title`, `kind` (`project` or `proficiency`),
and positive integer `version`. `source` is `human`, `ai-draft`, or `imported`.
Every node has an existing `level`, a unique stable `id`, a `title`, S/M/L `size`,
a `done_when` of at least 15 characters, and an HTTP(S) `resource`.

Optional `brief` text introduces a concrete challenge. Optional `steps` and `hints`
are lists of nonempty strings, with the same variable and series substitutions as
other content. The started challenge workspace displays steps in order and keeps hints
behind individual disclosures. These are learning guidance, not completion
checks; `done_when` and the verifier still define the finish line. Older packs
without them continue to work. Prefer a small observable result over a reading
assignment, and set honest `minutes` estimates so short sessions have useful tasks.

Optional `preview` is a short objective shown before Start. `requirements` lists
only prerequisite tools, access, hardware and costs. Keep task files, commands,
answers and detailed completion criteria out of these fields. Older packs without
them use the title as the preview. Optional `setup` contains workspace preparation
instructions shown **after** Start, along with the full task. `resource_label` and `resource_note` describe the role of the
reference (for example, optional free documentation). `materials` is a list of
`{label, url}` objects for actual inputs. URLs accept HTTP(S) or bundled
`/training/<name>.zip` (also JSON/CSV/TXT) paths, never arbitrary local files.
Fenced code blocks in `steps` render as copyable text; copying does not execute
commands. See [the authoring checklist](curriculum/challenge-authoring.md).

Web overview/list endpoints return previews; `/api/challenges/PACK:NODE` returns
full guidance only for an existing task session or completed node. Ended attempts
retain review access. These presentation rules do not conceal the public TOML
authoring files or impose a new completion check on the CLI.

S/M/L conservatively fit 30/120/240-minute budgets. Optional integer `minutes`
may refine the estimate within that size bound. `needs` is a list of node IDs
forming a directed acyclic graph. `series = {from = 13, to = 15}` expands an ID
`exercise` to `exercise-13`, `exercise-14`, `exercise-15`, chained in order. `{n}`
and `{next}` are substituted. The first expanded node inherits the original needs.

Main levels gate on the previous main level. Milestones (`milestone = true`)
replace the all-node gate when present. Proficiency packs require 8–15 main
levels and at least one M/L milestone per main level. Side levels are always
open but individual prerequisites still apply. `gate = false` bypasses a level
gate. `ascend unlock <level>` records an explicit early unlock.

`[vars]` values substitute `{name}` placeholders; local verifier paths expand `~`.
For commands, the template is split into arguments **before** substitution.
Shell operators are not interpreted. A command containing pipelines or redirects
must be rewritten as an executable script and trusted deliberately.

Install with `ascend pack install <file-or-bundled-id>`. Private copies live under
`ASCEND_HOME/packs/<user-id>/`. Editing a copy resets trust and review state.
`ascend pack diff <updated-file>` reports added/removed IDs; progress is retained
for stable IDs. `ascend pack review <id>` records review without editing the file.

Available checks: `manual`, `file`, `command`, `http`, `git`, and `plugin:<name>`.
`auto_complete = true` permits passing hard local file/command checks to complete
without a separate confirmation. `ascend sync` proposes other unlocked results;
`ascend accept` reruns the checks before accepting. Known evidence timestamps
produce deduplicated entries on their actual logical day, unless
`ascend config auto-counts-for-streak false` is set.

`ascend split <node> "first small result" "second small result"` stores a local
10-minute-step breakdown in SQLite; the TOML input stays untouched. Choose parts
that together satisfy the parent's original completion condition.
