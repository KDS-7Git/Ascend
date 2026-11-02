# Writing usable challenges

The 2026-11-02 repair replaces repeated starter/transfer placeholders and supplies
concrete inputs and instructions across the 19 generated specialist tracks. It
also identifies packet inputs in the older networking and SIEM tracks. The audit
scans all 28 bundled packs (1,002 expanded nodes). It checks known defects; zero
findings is **not** proof that every task is effective or every external lab runs.

A challenge must tell the learner:

1. What small result they are trying to produce.
2. Which environment, tools, accounts, hardware and costs are involved, before timing.
3. Exactly where inputs come from: a named download, inline fixture, or an earlier
   task with explicit files. Do not say “supplied dataset” without supplying it.
4. What actions to perform and what observations to inspect. Guided practice needs
   usable steps; an implementation assignment can leave code to the learner but
   must specify inputs, constraints, required behavior and a valid comparison.
5. What to retain and how to save it. The report helper prompts for the learner's
   own observations; it neither answers nor grades the challenge.
6. What constitutes completion and what remains untested. A file check verifies
   presence/size only. An offline model cannot demonstrate operational AD, cloud,
   mobile, memory-analysis, radio or Kubernetes behavior.

Use short summaries. Put full instructions in `steps`, copyable fenced commands
inside those steps, environment details in `setup`, and downloads in `materials`.
Use `resource_label`/`resource_note` to distinguish optional references from lab
access. A published course syllabus can inform track coverage without becoming
the required resource for every task in that track.

## Source and build flow

- `specialist-paths.json`: stable IDs, prerequisites, concept scenarios,
  experiment/assessment objectives and individually authored overrides.
- `lab-guides.json`: concrete per-track setup, starter recipe, six topic recipes
  and a specified independent variation. This is authored content, not a prompt
  sent to a model at runtime.
- `tracks/cyber-tracks/materials/<track>/`: inspectable original fixture sources.
  The shared `report.py` is added to each archive during packaging. No dataset
  here is evidence of a real incident. Deliberately incomplete toy services bind
  loopback and use only synthetic records.
- `scripts/build_specialist_tracks.py`: applies guides and optional task-specific
  overrides to both runtime TOML and public exports. Overrides cannot change IDs,
  prerequisites or verifiers. It also builds scenario/catalog/assessment indexes.
- `scripts/build_packet_fixtures.py`: creates deterministic HTTP and 802.11 PCAPs
  without transmitting or capturing packets. Wireshark decoding checks their
  stated HTTP statuses, link type, channel and RSN fields.
- `scripts/package_learning_materials.py`: makes deterministic per-track ZIPs in
  `web/training`. Packaging does not execute scripts. The web assets are included
  in wheels/source distributions through the existing recursive packaging.

Run the generators after changing canonical sources, then their `--check` modes
(packet fixtures are checked by tests), `scripts/build_registry.py`, and
`scripts/audit_learning_content.py`. CI detects stale packs, missing/stale ZIPs
and stale audit output. `tests/test_learning_materials.py` also rejects known
instruction patterns and exercises representative local recipes. Existing stable
IDs preserve progression; historical completions are not retroactively evidence
for the revised tasks.

## What was tested, and what still requires a real environment

Automated checks execute the published first HTTP recipe, the packaged local API,
marker/cleanup, permission model, benign source sample and deterministic assistant;
validate timestamp controls and report persistence; decode the synthetic captures;
and exercise downloads/copying/layout/session reload in Chromium at mobile and
desktop widths. Other fixture content receives structural/content review.

This change does **not** claim execution of Windows domain/AD CS labs, Android
emulators, provider IAM policies, a Kubernetes cluster, Security Onion imports,
Volatility memory analysis, physical devices or every cryptographic/MQTT task.
Those tasks name their environment and distinguish setup progress from operational
completion. A public URL responding successfully is only a reachability check.

The generic report helper asks nine questions and creates the requested JSON with
exclusive file creation. Empty input/cancellation leaves no report, and an existing
report is preserved. It writes only when the learner runs it. A hosted Ascend
server cannot see files saved solely on a laptop: the learner must place evidence
at the server's configured lab path. There is no upload feature in this change.

Private installed packs do not update automatically when bundled files change.
Back up SQLite and private pack files before deployment, preserve learner state,
and verify active sessions before replacing content. Changed pack fingerprints
reset trust and can invalidate unfinished generated exercises; do not silently
discard a learner's active attempt during an update.
