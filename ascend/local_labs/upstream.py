"""Per-exercise upstream feedback contracts; these never launch an unreviewed lab."""

import hashlib
import json
from pathlib import Path

from ascend.local_labs.catalog import detail
from ascend.local_labs.checks import bounded, local_report, outcome

SUPPORTED = {"labtainers-network-basics", "labtainers-telnetlab", "restaurant-profile-repair",
             "bgp-single-session", "bgp-session-protection", "bgp-prefix-filter",
             "kubernetes-goat-rbac", "cloudfoxable-secret", "mastg-android-storage",
             "mbe-intro-reversing", "llm-agent-transactions"}


def report_recipe(recipe_id):
    recipe = detail(recipe_id)
    if recipe_id not in SUPPORTED or not recipe.get("evidence_reviewed") or recipe.get("grading") not in {"upstream-report-v1", "local-report-v1"}:
        raise ValueError("No reviewed upstream evidence contract for this recipe")
    return recipe


def plan(recipe_id):
    recipe = detail(recipe_id)
    return {"recipe_id": recipe_id, "runnable": recipe["runnable"], "source": recipe.get("source"),
            "setup": recipe.get("integration", {}), "requirements": recipe.get("required_tools", []),
            "availability_reason": recipe.get("availability_reason"), "review_gaps": recipe.get("review_gaps", []),
            "report_template": recipe.get("report_template"), "evidence_authority": "local",
            "capability": recipe.get("capability"), "selected_files": recipe.get("assets", []),
            "instructions": recipe.get("instructions"), "evidence_label": recipe.get("evidence_label"),
            "commands_are_executed": False}


def validate_report(recipe, report):
    bounded(report)
    if "evidence" in report:
        from ascend.local_labs.evidence import validate

        if set(report) - {"evidence", "source_report_sha256"}:
            raise ValueError("Unexpected evidence report fields")
        return validate(recipe, report["evidence"])
    provider = recipe["integration"]["provider"]
    if report.get("exercise") != recipe["integration"]["exercise"]:
        raise ValueError("Upstream report belongs to a different exercise")
    if set(report) - {"exercise", "checks", "exit_code", "source_report_sha256", "upstream_exploit_exit", "upstream_unit_exit", "environment"}:
        raise ValueError("Unexpected upstream report fields")
    source_hash = report.get("source_report_sha256")
    if source_hash is not None:
        import re

        if not isinstance(source_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", source_hash):
            raise ValueError("Invalid report digest")
    if provider == "specialist-observations":
        if set(report) & {"exit_code", "upstream_exploit_exit", "upstream_unit_exit"}:
            raise ValueError("A command exit code is not a specialist observation")
        environment = report.get("environment")
        if not isinstance(environment, dict) or set(environment) != set(recipe["environment_fields"]):
            raise ValueError("Record exactly the selected exercise's environment fields")
        if any(not isinstance(v, str) or not 1 <= len(v.strip()) <= 256 for v in environment.values()):
            raise ValueError("Environment fields must be nonempty text of at most 256 characters")
        if environment["source_revision"] != recipe["source"]["revision"]:
            raise ValueError("Specialist observations use a different source revision")
        for name in recipe.get("digest_environment_fields", []):
            import re

            if not re.fullmatch(r"[a-f0-9]{64}", environment[name]):
                raise ValueError("Record the SHA-256 digest for " + name)
        if recipe.get("minimum_trials") and (not environment["trial_count"].isdigit() or not recipe["minimum_trials"] <= int(environment["trial_count"]) <= 10000):
            raise ValueError("Record at least three trials; one result does not characterize a model")
        result = local_report({"checks": report.get("checks")}, recipe)
        result.update(evidence_label="Practice recorded (manual observations)", environment=environment,
                      detail=recipe["check_meaning"] + " These are the learner's reported observations and environment identifiers; Ascend did not run or verify this environment.")
        if source_hash:
            result["source_report_sha256"] = source_hash
        return result
    if "environment" in report:
        raise ValueError("This upstream report does not accept environment fields")
    if provider == "labtainers" and not recipe["check_ids"]:
        return outcome([], detail="This pinned network-basics goals.config is empty. Results record SSH/tcpdump and ARP observations, but there is no automatic grade. Instructor review is separate.")
    if provider == "netlab":
        code = report.get("exit_code")
        if type(code) is not int or not 0 <= code <= 3:
            return outcome([{"id": "netlab_execution", "status": "error"}], detail="netlab did not return a recognized validation result")
        if code in {2, 3}:
            return outcome([{"id": "netlab_validation", "status": "unsupported"}], detail="No usable checkset" if code == 2 else "netlab reported warnings; this is not a complete pass")
        result = local_report({"checks": report.get("checks")}, recipe)
        if (code == 0 and result["status"] != "pass") or (code == 1 and result["status"] != "fail"):
            raise ValueError("netlab exit code and check results disagree")
    elif provider == "restaurant" and "checks" not in report:
        # Upstream game.py treats pytest exit 1 on an exploitation test as a fix.
        # A failing assertion alone is not proof of the desired repaired behavior.
        return outcome([{"id": "repair_evidence", "status": "unsupported"}], detail="Upstream exploitation-test failure plus a green unit suite is insufficient for an Ascend repair result. Supply the named owner, cross-user, changed-object and anonymous observations; these still remain local evidence.")
    else:
        result = local_report({"checks": report.get("checks")}, recipe)
    result["detail"] = recipe["check_meaning"] + " This imported report is learner-controlled; no trusted runner observed the environment."
    if source_hash:
        result["source_report_sha256"] = source_hash
    return result


def read_report(recipe, path):
    path = Path(path).expanduser()
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 1_000_000:
        raise ValueError("Use a regular JSON report smaller than 1 MB; keep .lab archives local for instructor review")
    content = path.read_bytes()
    report = bounded(json.loads(content))
    if recipe["integration"]["provider"] == "labtainers" and "exercise" not in report:
        # Read the real Labtainers instructor JSON shape. Extra historical goals
        # are not scored: the pinned current goals.config defines our subset.
        records = [v for k, v in report.items() if k.endswith("." + recipe["integration"]["exercise"]) and isinstance(v, dict)]
        if len(records) != 1 or not isinstance(records[0].get("grades"), dict):
            raise ValueError("Choose one Labtainers exercise report")
        grades = records[0]["grades"]
        if any(type(grades.get(name)) is not bool for name in recipe["check_ids"]):
            raise ValueError("Selected Labtainers goals are missing or malformed")
        report = {"exercise": recipe["integration"]["exercise"], "checks": [
            {"id": name, "status": "pass" if grades[name] else "fail"} for name in recipe["check_ids"]]}
    report["source_report_sha256"] = hashlib.sha256(content).hexdigest()
    validate_report(recipe, report)
    return report


class EvidenceOnly:
    """A terminal record of externally run work, with no provider resources."""

    def __init__(self, runtime):
        self.runtime = runtime

    def destroy(self, row):
        return None

    def submission(self, row):
        return {"report": self.runtime.read_work(row, "upstream-report.json")}
