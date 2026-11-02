"""Local permission model, not an AWS/Azure/GCP policy evaluator."""
import json
from pathlib import Path
config=json.loads(Path("cloud.json").read_text())
def allowed(role, action):
    return action in config["roles"].get(role, [])
if __name__ == "__main__":
    for role in ("reader","editor","unknown"):
        for action in ("read","write"):
            print(role,action,allowed(role,action))
