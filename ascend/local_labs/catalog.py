"""Small shared catalog; repository discovery is deliberately not code execution."""

import json
import re
from pathlib import Path

DATA = Path(__file__).parent / "resources"
# Add an adapter here only with its fixed implementation and lifecycle contract.
ADAPTERS: frozenset[str] = frozenset(
    {
        "security-audit-v1",
        "vampi-v1",
        "prefix-policy-v1",
        "wrongsecrets-v1",
        "frr-bgp-v1",
    }
)
LOCATIONS = {
    "local-files",
    "local-container",
    "local-vm",
    "local-cluster",
    "cloud",
    "external",
}


def references():
    return json.loads((DATA / "catalog.json").read_text())["references"]


def recipes():
    return [
        json.loads(path.read_text())
        for path in sorted((DATA / "recipes").glob("*.json"))
    ]


def review_gaps(recipe):
    """Fail closed, including when a catalog editor sets status=reviewed too early."""
    gaps = []
    if recipe.get("status") != "reviewed":
        gaps.append("Runtime review is incomplete")
    if recipe.get("adapter") not in ADAPTERS:
        gaps.append("No reviewed adapter")
    if not re.fullmatch(r"[0-9a-f]{40}", recipe.get("source", {}).get("revision", "")):
        gaps.append("Source revision is not pinned")
    if not recipe.get("license_review"):
        gaps.append("Selected exercise license needs review")
    if not recipe.get("version") or not recipe.get("checker_version"):
        gaps.append("Recipe and checker versions are required")
    assets = recipe.get("assets", [])
    if not assets or any(
        not re.fullmatch(r"[0-9a-f]{64}", a.get("sha256", ""))
        or not a.get("url", "").startswith("https://")
        or type(a.get("bytes")) is not int
        or a["bytes"] <= 0
        for a in assets
    ):
        gaps.append("Selected downloads need sizes and SHA-256 pins")
    if not recipe.get("tested_platforms"):
        gaps.append("Linux platform has not been measured")
    metrics = recipe.get("measurements", {})
    for name in (
        "download_bytes",
        "expanded_bytes",
        "peak_disk_bytes",
        "startup_cold_seconds",
        "startup_warm_seconds",
        "peak_memory_bytes",
    ):
        if type(metrics.get(name)) not in (int, float) or metrics[name] < 0:
            gaps.append(f"Missing measured {name}")
    if not recipe.get("lifecycle_verified") or not recipe.get("verification_report"):
        gaps.append("Lifecycle and negative/control tests need evidence")
    if recipe.get("adapter") in {"vampi-v1", "wrongsecrets-v1"}:
        if not re.fullmatch(
            r"[a-z0-9./_-]+@sha256:[a-f0-9]{64}",
            recipe.get("image", {}).get("reference", ""),
        ):
            gaps.append("Container image digest is not pinned")
        if not recipe.get("image_source_audit") or not re.fullmatch(
            r"[a-f0-9]{64}", recipe.get("launcher_sha256", "")
        ):
            gaps.append("Image source and launcher need review")
        if not re.fullmatch(r"[a-f0-9]{64}", recipe.get("proxy_sha256", "")):
            gaps.append("Loopback proxy needs a reviewed hash")
        if recipe["adapter"] == "wrongsecrets-v1" and not re.fullmatch(
            r"[a-z0-9./_-]+@sha256:[a-f0-9]{64}",
            recipe.get("helper_image", {}).get("reference", ""),
        ):
            gaps.append("Subset proxy image needs a pinned digest")
    if recipe.get("adapter") == "prefix-policy-v1" and (
        not re.fullmatch(r"[a-f0-9]{64}", recipe.get("worker_sha256", ""))
        or not recipe.get("worker_review")
    ):
        gaps.append("Policy worker needs a reviewed revision and execution contract")
    if recipe.get("adapter") == "frr-bgp-v1":
        if not re.fullmatch(
            r"[a-z0-9./_-]+@sha256:[a-f0-9]{64}",
            recipe.get("image", {}).get("reference", ""),
        ):
            gaps.append("Container image digest is not pinned")
        if not recipe.get("image_source_audit") or not re.fullmatch(
            r"[a-f0-9]{40}", recipe.get("frr_source_revision", "")
        ):
            gaps.append("FRR image source and license need review")
        if any(
            not re.fullmatch(r"[a-f0-9]{64}", recipe.get(key, ""))
            for key in ("adapter_sha256", "launcher_sha256")
        ):
            gaps.append("BGP adapter and launcher need reviewed hashes")
    return gaps


def recipe_detail(recipe):
    result = dict(recipe)
    result["review_gaps"] = review_gaps(recipe)
    result["runnable"] = not result["review_gaps"]
    result["satisfies_track_evidence"] = False
    result["local_workflow"] = bool(
        recipe.get("evidence_reviewed") and recipe.get("report_template")
    )
    return result


def catalog(*, track=None, level=None, location=None, search=None):
    if location and location not in LOCATIONS:
        raise ValueError("Unknown lab execution location")
    if level and level not in {"starter", "intermediate", "advanced"}:
        raise ValueError("Unknown lab level")
    reviewed = recipes()
    result = []
    for ref in references():
        selected = [r for r in reviewed if r["reference_id"] == ref["id"]]
        if track and track not in ref["track_ids"]:
            continue
        if level and level not in ref["levels"]:
            continue
        if (
            location
            and location != ref["location"]
            and not any(r.get("location") == location for r in selected)
        ):
            continue
        if search and search.casefold() not in json.dumps([ref, selected]).casefold():
            continue
        row = dict(ref)
        row["recipes"] = [recipe_detail(r) for r in selected]
        row["runnable"] = any(r["runnable"] for r in row["recipes"])
        row["status"] = "reviewed-recipes" if row["runnable"] else "reference"
        result.append(row)
    return result


def detail(lab_id):
    for ref in catalog():
        if ref["id"] == lab_id:
            return ref
        for recipe in ref["recipes"]:
            if recipe["id"] == lab_id:
                return {
                    **recipe,
                    "reference": {k: v for k, v in ref.items() if k != "recipes"},
                }
    raise ValueError("Unknown lab or recipe")


def executable(lab_id):
    recipe = detail(lab_id)
    if not recipe.get("adapter") or not recipe.get("runnable"):
        raise ValueError(
            "This is a reference, not a reviewed executable recipe: "
            + "; ".join(recipe.get("review_gaps", []))
        )
    return recipe
