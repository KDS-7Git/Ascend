"""Portable preparation and artifact capture for learner-managed lab runtimes."""

import json
import secrets
import shlex
import shutil
import time
from pathlib import Path, PurePosixPath

from ascend.local_labs import evidence
from ascend.local_labs.assets import AssetStore, atomic_json
from ascend.local_labs.upstream import report_recipe


def prepare(runtime, recipe_id):
    recipe = report_recipe(recipe_id)
    if recipe_id not in evidence.PROFILES:
        raise ValueError("No local evidence workflow for this recipe")
    with runtime.lock():
        row = {
            "schema_version": 1,
            "id": secrets.token_hex(16),
            "owner": runtime.owner(),
            "recipe": recipe,
            "status": "destroyed",
            "resources": {},
            "evidence_only": True,
            "external_workspace": True,
            "created_at": time.time(),
            "expires_at": time.time(),
            "server": runtime.server,
            "offline": True,
            "pending_sync": False,
        }
        runtime.save(row)
        work = runtime.work_dir(row)
        work.mkdir(parents=True, exist_ok=True, mode=0o700)
        downloaded = 0
        try:
            for asset in recipe["assets"]:
                rel = PurePosixPath(asset["path"])
                if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                    raise ValueError("Unsafe selected-source path")
                path, size = AssetStore(runtime.cache).fetch(asset)
                downloaded += size
                target = work / "references" / Path(*rel.parts)
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                shutil.copyfile(path, target)
            sample = evidence.template(recipe)
            atomic_json(work / "environment.json", sample["environment"])
            atomic_json(work / "artifact-templates.json", sample["artifacts"])
            atomic_json(
                work / "evidence.json",
                {
                    "schema_version": evidence.VERSION,
                    "recipe_id": recipe_id,
                    "source_revision": recipe["source"]["revision"],
                    "environment": sample["environment"],
                    "artifacts": {},
                },
            )
            atomic_json(work / "upstream-plan.json", recipe["integration"])
            from ascend.local_labs.collectors import config_template

            atomic_json(work / "collector.json", config_template(recipe))
            (work / "README.md").write_text(instructions(row, work))
            row["metrics"] = {"download_bytes": downloaded, "runtime_started": False}
            row["prepared"] = True
            row["files"] = {
                "instructions": str(work / "README.md"),
                "environment": str(work / "environment.json"),
                "templates": str(work / "artifact-templates.json"),
                "plan": str(work / "upstream-plan.json"),
                "collector": str(work / "collector.json"),
            }
            runtime.save(row)
        except BaseException:
            row["preparation_failed"] = True
            runtime.save(row)
            raise
        return runtime.public(row)


def instructions(row, work):
    r, run = row["recipe"], row["id"]
    lines = [
        f"# {r['title']}",
        "",
        "Run the actual lab on your own PC, disposable VM, cluster or configured account.",
        "This workspace downloads selected pinned reference files. It does not install or launch the upstream environment.",
        "",
        f"Source: {r['source']['repository']} at `{r['source']['revision']}`.",
        "",
        r["instructions"],
        "",
        "## Run locally",
        "",
        f"Required tools: {', '.join(r['required_tools'])}.",
        "The complete upstream setup and its exact reviewed exercise are in `upstream-plan.json`.",
        "Selected reference files are in `references/`; they are not the complete upstream installation.",
        "",
    ]
    for step in ("acquisition", "start", "check", "stop", "export", "destroy"):
        value = r["integration"].get(step)
        if value:
            lines += [
                f"### {step.capitalize()}",
                "",
                "```json",
                json.dumps(value, indent=2),
                "```",
                "",
            ]
    acquisition = r["integration"].get("acquisition", [])
    if acquisition:
        lines += [
            "### Copyable source acquisition",
            "",
            "Run these commands on the chosen lab machine. Replace the destination if this workspace is on another PC.",
            "",
            "```sh",
        ]
        lines += [
            shlex.join(
                str(work / "upstream") if arg == "ROOT" else arg for arg in command
            )
            for command in acquisition
        ]
        lines += ["```", ""]
    lines += [
        "## Save and review evidence",
        "",
        "Fill `environment.json` with the actual environment identifiers and hashes.",
        "Use only synthetic test accounts and values. Keep passwords, cloud credentials, tokens, Terraform state, VM disks and full model traces on your PC.",
        "For each artifact in `artifact-templates.json`, save the corresponding bounded observation as a JSON object.",
        "Capture actual tool output and outcomes, including the negative control; a `passed: true` declaration is not accepted.",
        "For supported local tools, fill `collector.json`, then run `ascend local-lab observe RUN ARTIFACT` to collect the read-only observation directly.",
        "Collectors explicitly select the kubeconfig/context, emulator serial, AWS profile or FRR container. They do not start, modify or delete those environments.",
        "",
        "```sh",
    ]
    lines += [
        f"ascend local-lab capture {run} {name} /path/to/{name}.json"
        for name in evidence.artifact_names(r)
    ]
    lines += [
        f"ascend local-lab check {run}",
        f"ascend local-lab finish {run}",
        f"ascend local-lab sync {run}",
        "```",
        "",
        "Check can be repeated while gathering evidence. Missing artifacts remain unsupported. Finish saves a local receipt; sync is explicit.",
        "The server repeats artifact checks and binds the result to your account, attempt, source and checker versions.",
        "Locally captured output can be modified by its owner. Artifact hashes establish consistency and do not authenticate the earlier environment.",
        "These results award no verified-track credit or XP. They do not prove how a solution was obtained.",
        "",
        "## Cleanup",
        "",
        "Follow the upstream destroy instructions and retain its resource inventory until destruction is confirmed.",
        "Ascend never deletes your VM, cloud resources, emulator or a shared model store from an evidence workspace.",
        "Source-cache eviction preserves these notes, captured artifacts and exports.",
        "",
    ]
    return "\n".join(lines)


def workspace(runtime, run_id):
    row = runtime.load(run_id)
    if (
        not row.get("external_workspace")
        or not row.get("prepared")
        or row.get("preparation_failed")
        or row.get("archived")
    ):
        raise ValueError("Use a successfully prepared local evidence workspace")
    return row


def capture(runtime, run_id, name, path):
    with runtime.lock():
        row = workspace(runtime, run_id)
        if row.get("finished_at"):
            raise ValueError("This evidence receipt is final; prepare a new workspace")
        if name not in evidence.artifact_names(row["recipe"]):
            raise ValueError("Unknown artifact name for this lab")
        path = Path(path).expanduser()
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > evidence.LIMIT
        ):
            raise ValueError("Capture a regular JSON object file of at most 64 KiB")
        try:
            content = json.loads(path.read_bytes())
        except (ValueError, RecursionError):
            raise ValueError("Artifact must contain a JSON object") from None
        evidence.bounded(content, evidence.LIMIT)
        package = runtime.read_work(row, "evidence.json")
        package["artifacts"][name] = {
            "sha256": evidence.content_hash(content),
            "content": content,
        }
        # Bound the complete package before writing it, not only each file.
        evidence.bounded(package)
        atomic_json(runtime.work_dir(row) / "evidence.json", package)
        runtime.save(row)
        return {
            "path": str(runtime.work_dir(row) / "evidence.json"),
            "bytes": len(json.dumps(package).encode()),
            "authority": "local",
        }


def review(runtime, row):
    package = runtime.read_work(row, "evidence.json")
    package["environment"] = runtime.read_work(row, "environment.json")
    result = evidence.validate(row["recipe"], package)
    atomic_json(runtime.work_dir(row) / "evidence.json", package)
    row["last_check"] = result
    runtime.save(row)
    return result


def finish(runtime, run_id):
    with runtime.lock():
        row = workspace(runtime, run_id)
        if row.get("finished_at"):
            return runtime.public(row)
        review(runtime, row)
        package = runtime.read_work(row, "evidence.json")
        atomic_json(
            runtime.work_dir(row) / "upstream-report.json", {"evidence": package}
        )
        data = runtime._export(row)
        attempt = row.get("local_attempt")
        if not attempt:
            attempt = runtime.attempts.create(row["recipe"]["id"], offline=True)
            row["local_attempt"] = attempt
            runtime.save(row)
        row["local_receipt"] = runtime.attempts.submit(
            attempt["id"], runtime._payload(row, attempt, data)
        )
        row["finished_at"] = time.time()
        row["pending_sync"] = bool(row.get("server") or runtime.server)
        runtime.save(row)
        return runtime.public(row)
