"""Generate the bundled registry from the base catalog and domain fragments."""

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "packs/community"


def document(root=ROOT):
    catalog = {}
    for path in [root / "catalog.json", *sorted(root.glob("*/catalog.json"))]:
        if not path.exists():
            continue
        for row in json.loads(path.read_text())["tracks"]:
            if row["id"] in catalog:
                raise ValueError(f"Duplicate catalog ID: {row['id']}")
            catalog[row["id"]] = row
    packs, seen = [], set()
    for path in sorted(root.rglob("*.toml"), key=lambda path: path.name):
        raw = path.read_bytes()
        meta = tomllib.loads(raw.decode())["pack"]
        if meta["id"] in seen:
            raise ValueError(f"Duplicate bundled pack ID: {meta['id']}")
        seen.add(meta["id"])
        packs.append(
            {
                **catalog.get(meta["id"], {}),
                "id": meta["id"],
                "title": meta["title"],
                "version": meta["version"],
                "file": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    missing = set(catalog) - seen
    if missing:
        raise ValueError("Catalog entries have no pack: " + ", ".join(sorted(missing)))
    for entry in packs:
        unknown = set(entry.get("recommended_after", [])) - seen
        if unknown:
            raise ValueError(
                f"Unknown recommended tracks for {entry['id']}: {sorted(unknown)}"
            )
    return {"version": 1, "packs": packs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = json.dumps(document(), indent=2) + "\n"
    path = ROOT / "registry.json"
    if args.check:
        if not path.exists() or path.read_text() != text:
            raise SystemExit(
                "Bundled registry is stale. Run scripts/build_registry.py."
            )
    else:
        path.write_text(text)
    print("Bundled registry is consistent.")


if __name__ == "__main__":
    main()
