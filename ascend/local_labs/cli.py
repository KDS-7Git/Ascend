"""Client commands are deliberately kept outside the HTTP command transport."""


def add_parser(sub):
    lab = sub.add_parser(
        "local-lab", help="Run reviewed labs on this Linux PC"
    ).add_subparsers(dest="action", required=True)
    for action in ("doctor", "start"):
        child = lab.add_parser(action)
        child.add_argument("recipe")
        if action == "start":
            child.add_argument(
                "--offline",
                action="store_true",
                help="Record practice locally and sync later without a trusted timer",
            )
            child.add_argument(
                "--lifetime",
                type=int,
                default=7200,
                help="Seconds until reconciliation expires this runtime",
            )
    for action in (
        "show",
        "check",
        "stop",
        "resume",
        "reset",
        "export",
        "finish",
        "destroy",
        "sync",
    ):
        lab.add_parser(action).add_argument("run")
    lab.add_parser("history")
    lab.add_parser("reconcile")
    record = lab.add_parser(
        "record", help="Import bounded feedback from an externally run lab"
    )
    record.add_argument("recipe")
    record.add_argument(
        "report", help="Local JSON report; original lab archives remain on this PC"
    )
    prepare = lab.add_parser(
        "prepare",
        help="Prepare pinned references and evidence capture for a learner-managed lab",
    )
    prepare.add_argument("recipe")
    capture = lab.add_parser(
        "capture", help="Capture one bounded artifact for a prepared local lab"
    )
    capture.add_argument("run")
    capture.add_argument("artifact")
    capture.add_argument("path")
    observe = lab.add_parser(
        "observe",
        help="Collect one read-only observation using the workspace's explicit environment",
    )
    observe.add_argument("run")
    observe.add_argument("artifact")
    cache = lab.add_parser("cache")
    cache.add_argument("--budget-mib", type=int, default=128)
    cache.add_argument(
        "--images",
        action="store_true",
        help="Also remove unused images acquired by this companion",
    )


def execute(tracker, args):
    if getattr(tracker, "server_mode", False):
        raise ValueError("Local lab operations must run on the learner PC")
    from ascend.local_labs.runtime import Runtime

    runtime = Runtime(tracker, server=getattr(args, "local_server", None))
    action = args.action
    if action == "doctor":
        return runtime.doctor(args.recipe)
    if action == "start":
        import sys

        def preparing(report):
            print(
                f"Preparing {args.recipe} on this PC. First-download budget: {report['first_download_bytes'] / 1048576:.1f} MiB; cached assets are reused. Saved work: {report['work']}",
                file=sys.stderr,
            )

        return runtime.start(
            args.recipe,
            offline=args.offline,
            lifetime=args.lifetime,
            on_prepare=preparing,
        )
    if action == "record":
        return runtime.record(args.recipe, args.report)
    if action == "prepare":
        return runtime.prepare(args.recipe)
    if action == "capture":
        return runtime.capture(args.run, args.artifact, args.path)
    if action == "observe":
        from ascend.local_labs.collectors import observe

        return observe(runtime, args.run, args.artifact)
    if action in {"history", "reconcile"}:
        return getattr(runtime, action)()
    if action == "cache":
        return runtime.prune(args.budget_mib, args.images)
    return getattr(runtime, action)(args.run)


def render(result):
    if isinstance(result, list):
        return (
            "\n".join(
                f"{r.get('id', 'recovery')}: {r['status']} · {r.get('recipe', {}).get('title', r.get('error', ''))}"
                for r in result
            )
            or "No local lab runs."
        )
    if "issues" in result:
        lines = [
            f"{result['recipe_id']}: {result['status']} ({result['platform']})",
            *result["issues"],
            f"First-download budget: {result['first_download_bytes'] / 1048576:.1f} MiB",
            f"Free disk: {result['free_bytes'] / 1048576:.1f} MiB",
            f"Saved work: {result['work']}",
        ]
        if result.get("provider"):
            lines.append(
                f"Docker storage free: {result['provider']['free_bytes'] / 1048576:.1f} MiB"
            )
    elif "cache_bytes" in result:
        lines = [
            f"Source cache: {result['cache_bytes']} bytes; removed {len(result['removed'])} objects. Saved work retained."
        ]
        if result.get("images"):
            lines.append(
                f"Images removed: {len(result['images']['removed'])}; retained: {len(result['images']['retained'])}; errors: {len(result['images']['errors'])}"
            )
    elif "path" in result:
        lines = [f"Saved {result['path']} ({result['bytes']} bytes; local evidence)"]
    elif "checks" in result:
        lines = [
            f"{result['evidence_label']}: {result['status']}",
            *[f"  {c['id']}: {c['status']}" for c in result["checks"]],
            result.get("detail") or "",
        ]
    else:
        lines = [f"{result.get('id', '')}: {result.get('status', '')}"]
        if result.get("recipe"):
            lines.append(result["recipe"]["title"])
        for key, value in result.get("files", {}).items():
            lines.append(f"{key}: {value}")
        for key, value in result.get("endpoints", {}).items():
            lines.append(f"{key}: {value}")
        for key, value in result.get("connect_commands", {}).items():
            lines.append(f"Connect {key}: {value}")
        if result.get("addresses"):
            lines.append(
                "Router addresses: "
                + ", ".join(
                    f"{key}={value}" for key, value in result["addresses"].items()
                )
            )
        if result.get("work_dir"):
            lines.append("Saved work: " + result["work_dir"])
        if result.get("status") == "destroyed" and result.get("recipe", {}).get(
            "image"
        ):
            lines.append(
                "To reclaim unused downloads and images: ascend local-lab cache --budget-mib 0 --images"
            )
        for key in ("export", "cleanup_error", "sync_error", "error"):
            if result.get(key):
                lines.append(f"{key}: {result[key]}")
        if result.get("pending_sync"):
            lines.append(
                "Result saved locally; synchronize with local-lab sync " + result["id"]
            )
        receipt = result.get("remote_receipt", {}).get("result")
        if receipt:
            lines.append(receipt["evidence_label"] + ": " + receipt["status"])
    return "\n".join(lines)
