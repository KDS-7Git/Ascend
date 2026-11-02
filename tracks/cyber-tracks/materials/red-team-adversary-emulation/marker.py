"""Create and remove one harmless marker in this directory; log both actions."""
import json
from datetime import datetime, timezone
from pathlib import Path
marker=Path("training-marker.txt")
log=Path("marker-events.jsonl")
if marker.exists() or log.exists():
    raise SystemExit("Existing marker or log; preserve it and run in a fresh copy.")
with log.open("x") as output:
    with marker.open("x") as f:
        f.write("ASCEND TRAINING MARKER\n")
    output.write(json.dumps({"time":datetime.now(timezone.utc).isoformat(),"action":"create","path":str(marker)})+"\n")
    marker.unlink()
    output.write(json.dumps({"time":datetime.now(timezone.utc).isoformat(),"action":"remove","path":str(marker)})+"\n")
print(log.read_text())
print("Marker absent:",not marker.exists())
