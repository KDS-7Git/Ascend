"""Generate the bundled registry without fetching or trusting remote code."""
import hashlib
import json
from pathlib import Path
import tomllib

root = Path(__file__).resolve().parents[1] / "packs/community"
packs = []
for path in sorted(root.glob("*.toml")):
    raw = path.read_bytes()
    meta = tomllib.loads(raw.decode())["pack"]
    packs.append({"id": meta["id"], "title": meta["title"], "version": meta["version"],
                  "file": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
(root / "registry.json").write_text(json.dumps({"version": 1, "packs": packs}, indent=2) + "\n")
