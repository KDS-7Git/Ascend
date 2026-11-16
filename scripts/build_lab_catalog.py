"""Publish research references into the wheel; this does not activate any recipe."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLES = {
    "linux-upskill": "Linux Upskill Challenge",
    "labtainers": "Labtainers",
    "vampi": "VAmPI",
    "restaurant-api": "RESTaurant API Game",
    "wrongsecrets": "OWASP WrongSecrets",
    "stratocyberlab": "StratoCyberLab",
    "security-datasets": "Security Datasets",
    "evtx-samples": "EVTX Attack Samples",
    "kc7": "KC7",
    "bgp-labs": "BGP Labs",
    "rpisec-mbe": "RPISEC Modern Binary Exploitation",
    "cloudfoxable": "CloudFoxable",
    "kubernetes-goat": "Kubernetes Goat",
    "mastg-playground": "MASTG Hacking Playground",
    "vulnerable-llm-agent": "Damn Vulnerable LLM Agent",
}


def build():
    research = json.loads(
        (ROOT / "docs/curriculum/open-source-lab-candidates.json").read_text()
    )
    refs = []
    for item in research["candidates"]:
        row = dict(item)
        row["title"] = TITLES.get(item["id"], item["id"].replace("-", " ").title())
        row["location"] = (
            "external"
            if item["id"] == "kc7"
            else "cloud"
            if item["id"] == "cloudfoxable"
            else "local-files"
            if item["id"] in {"security-datasets", "evtx-samples"}
            else "local-cluster"
            if item["id"] == "kubernetes-goat"
            else "local-vm"
            if item["id"]
            in {
                "linux-upskill",
                "labtainers",
                "stratocyberlab",
                "rpisec-mbe",
                "mastg-playground",
            }
            else "local-container"
        )
        row["difficulty_basis"] = research["difficulty_basis"]
        row["automatic_execution"] = False
        refs.append(row)
    target = ROOT / "ascend/local_labs/resources/catalog.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"schema_version": 1, "references": refs}, indent=2) + "\n"
    )


if __name__ == "__main__":
    build()
