"""Generate the bundled registry without fetching or trusting remote code."""

import hashlib
import json
from pathlib import Path
import tomllib

root = Path(__file__).resolve().parents[1] / "packs/community"
packs = []
catalog_path = root / "catalog.json"
catalog = (
    {row["id"]: row for row in json.loads(catalog_path.read_text())["tracks"]}
    if catalog_path.exists()
    else {}
)
for path in sorted(root.rglob("*.toml"), key=lambda path: path.name):
    raw = path.read_bytes()
    meta = tomllib.loads(raw.decode())["pack"]
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
(root / "registry.json").write_text(
    json.dumps({"version": 1, "packs": packs}, indent=2) + "\n"
)
