"""Package deterministic, inspectable practice files. Never execute them here."""

import argparse
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "cyber": ROOT / "tracks/cyber-tracks/materials",
    "infrastructure": ROOT / "tracks/infrastructure-tracks/materials",
    "devops": ROOT / "tracks/devops-tracks/materials",
}
COMMON = ROOT / "tracks/engineering-common"
DEST = ROOT / "web/training"


def source_files(folder):
    if folder.is_symlink():
        raise ValueError(f"Material archives must contain regular files: {folder}")
    files = {}
    for path in folder.rglob("*"):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise ValueError(f"Material archives must contain regular files: {path}")
        if path.is_file():
            files[path.relative_to(folder).as_posix()] = path.read_bytes()
    return files


def outputs(domain=None):
    seen = set()
    for name, source in SOURCES.items():
        if domain and name != domain:
            continue
        if not source.exists():
            continue
        for folder in sorted(source.iterdir()):
            if not folder.is_dir() or folder.name == "shared":
                continue
            if folder.name in seen:
                raise ValueError(f"Duplicate material bundle: {folder.name}")
            seen.add(folder.name)
            files = source_files(folder)
            if name == "cyber":
                files["report.py"] = (source / "shared/report.py").read_bytes()
            else:
                if not COMMON.is_dir():
                    raise ValueError("Engineering common materials are missing")
                shared = {
                    "shared/" + key: value
                    for key, value in source_files(COMMON).items()
                }
                if set(shared) & set(files):
                    raise ValueError(f"Conflicting common material in {folder.name}")
                files.update(shared)
            files["LICENSE"] = (ROOT / "LICENSE").read_bytes()
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
                for member, data in sorted(files.items()):
                    info = zipfile.ZipInfo(
                        folder.name + "/" + member, (2026, 11, 2, 0, 0, 0)
                    )
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    archive.writestr(info, data)
            yield DEST / (folder.name + ".zip"), stream.getvalue()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--domain", choices=tuple(SOURCES))
    args = parser.parse_args()
    for path, data in outputs(args.domain):
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit("Stale learning materials: " + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Learning material archives are consistent.")
