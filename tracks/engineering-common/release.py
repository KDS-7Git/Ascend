"""Build, verify and select a Relay source artifact without a cloud service.

Selection atomically changes a local JSON pointer. A running process keeps its
old code until deliberately restarted; this is not a complete deployment daemon.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(artifact):
    artifact = Path(artifact).resolve()
    manifest = json.loads((artifact / "manifest.json").read_text())
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"format", "release", "revision", "files"}
        or type(manifest["format"]) is not int
        or manifest["format"] != 1
    ):
        raise ValueError("Unsupported artifact manifest")
    if not isinstance(manifest["release"], str) or not re.fullmatch(
        r"[A-Za-z0-9._-]{1,80}", manifest["release"]
    ):
        raise ValueError("Invalid release identifier")
    if not isinstance(manifest["revision"], str) or not manifest["revision"].strip():
        raise ValueError("Invalid source revision")
    if not isinstance(manifest["files"], dict) or manifest["files"].keys() != {
        "relay.py"
    }:
        raise ValueError("Artifact must contain exactly the declared Relay entrypoint")
    if {p.name for p in artifact.iterdir()} != {"relay.py", "manifest.json"}:
        raise ValueError("Unexpected artifact files")
    path = artifact / "relay.py"
    if (
        (artifact / "manifest.json").is_symlink()
        or path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > 2_000_000
    ):
        raise ValueError("Unsupported entrypoint")
    if digest(path) != manifest["files"]["relay.py"]:
        raise ValueError("Artifact content digest mismatch")
    return {
        "artifact": str(artifact),
        "release": manifest["release"],
        "revision": manifest["revision"],
        "manifest_sha256": digest(artifact / "manifest.json"),
    }


def build(source, destination, release, revision):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file() or source.stat().st_size > 2_000_000:
        raise ValueError("Source must be a Python file under 2 MB")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", release) or not revision.strip():
        raise ValueError("A release identifier and source revision are required")
    compile(source.read_text(), str(source), "exec")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        shutil.copyfile(source, destination / "relay.py")
        manifest = {
            "format": 1,
            "release": release,
            "revision": revision,
            "files": {"relay.py": digest(destination / "relay.py")},
        }
        (destination / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n"
        )
        return verify(destination)
    except Exception:
        shutil.rmtree(destination)
        raise


def select(artifact, state):
    selected = verify(artifact)
    state = Path(state).resolve()
    state.parent.mkdir(parents=True, exist_ok=True)
    lock = state.with_name(state.name + ".lock")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        os.close(fd)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=state.parent, prefix=".relay-release-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(selected, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, state)
        return selected
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def resolve(state):
    selected = json.loads(Path(state).read_text())
    actual = verify(selected["artifact"])
    if selected != actual:
        raise ValueError("Selected release changed; reverify before deployment")
    return actual


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="operation", required=True)
    b = commands.add_parser("build")
    b.add_argument("--source", default="shared/relay.py")
    b.add_argument("--out", required=True)
    b.add_argument("--release", required=True)
    b.add_argument("--revision", required=True)
    v = commands.add_parser("verify")
    v.add_argument("--artifact", required=True)
    s = commands.add_parser("select")
    s.add_argument("--artifact", required=True)
    s.add_argument("--state", default="deployment/current.json")
    r = commands.add_parser("resolve")
    r.add_argument("--state", default="deployment/current.json")
    run = commands.add_parser("serve")
    run.add_argument("--state", default="deployment/current.json")
    run.add_argument("relay_args", nargs=argparse.REMAINDER)
    args = cli.parse_args()
    try:
        if args.operation == "build":
            result = build(args.source, args.out, args.release, args.revision)
        elif args.operation == "verify":
            result = verify(args.artifact)
        elif args.operation == "select":
            result = select(args.artifact, args.state)
        else:
            result = resolve(args.state)
            if args.operation == "serve":
                forwarded = (
                    args.relay_args[1:]
                    if args.relay_args[:1] == ["--"]
                    else args.relay_args
                )
                if any(
                    x == "--release" or x.startswith("--release=") for x in forwarded
                ):
                    raise ValueError(
                        "The selected artifact supplies --release; do not override it"
                    )
                command = [
                    sys.executable,
                    str(Path(result["artifact"]) / "relay.py"),
                    "--release",
                    result["release"],
                    *forwarded,
                ]
                os.execv(sys.executable, command)
    except (OSError, ValueError, KeyError, SyntaxError) as error:
        cli.exit(1, "Release operation failed: " + str(error) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
