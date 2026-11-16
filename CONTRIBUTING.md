# Contributing to Ascend

Keep the daily loop small: one next step, honest evidence, an easy return tomorrow.
The engine is subject-independent. Put learning content in TOML packs, external
checks in verifier adapters, and shared behavior in the application layer.

## Development checks

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[server,dev]'
.venv/bin/playwright install chromium
.venv/bin/pytest -v
.venv/bin/python scripts/build_registry.py
```

Write regression tests for behavioral changes. Check both local and remote paths
when changing application semantics. Use descriptive commits with a focused
scope. Do not commit profiles, database files, actual network addresses, tokens,
or `.env` files. Regenerate and compile `docs/report.tex` at release milestones.

## Community packs

1. Add a generic pack to the matching [domain folder in `packs/community/`](packs/community/), using [the format reference](docs/pack-format.md). Keep its stable ID as the filename. Use `projects/` for general projects; cyber folders match the catalog category in lowercase.
2. Every `done_when` must name a concrete result the learner can demonstrate,
   preferably an artifact. A reading assignment alone is not a completion test.
3. Use real, relevant resource URLs. Check licenses before adapting others' maps.
   AI-generated material must retain `source = "ai-draft"` and `reviewed = false`
   until a human reviewer has read the complete pack.
4. Run `ascend pack lint <file>` and `ascend pack check-links <file>`. Resolve dead
   links; describe access restrictions such as 403/429 instead of inventing URLs.
5. Keep IDs stable across updates. Bump `pack.version` and document removed nodes.
6. Run `python scripts/build_registry.py` and submit the pack plus registry diff.

CI validates every pack and checksum without executing pack commands. Link checks
are explicit network operations and do not run on every offline test invocation.

## Third-party material

When adding or adapting third-party code, fonts, datasets, or learning materials,
record the authors, source revision, license, use, and modifications in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Preserve the original copyright
and full license notices with the material. Check the selected artifact's terms,
including attribution and source-distribution requirements; a repository link
alone is insufficient. Include required notices in the affected release packages.

## Verifiers

See [Writing a verifier](docs/writing-a-verifier.md). Never bypass the explicit
trust step or emit secrets as evidence. Include tests for failure, timeout, and
evidence timestamps. Plugins execute as the user; they are not sandboxed.
