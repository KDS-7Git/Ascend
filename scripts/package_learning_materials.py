"""Package deterministic, inspectable practice files. Never execute them here."""

import argparse
import io
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tracks/cyber-tracks/materials"
DEST = ROOT / "web/training"


def outputs():
    for folder in sorted(SOURCE.iterdir()):
        if not folder.is_dir() or folder.name == "shared":
            continue
        files = {
            p.relative_to(folder).as_posix(): p.read_bytes()
            for p in folder.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        files["report.py"] = (SOURCE / "shared/report.py").read_bytes()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(folder.name + "/" + name, (2026, 11, 2, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, data)
        yield DEST / (folder.name + ".zip"), stream.getvalue()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, data in outputs():
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit("Stale learning materials: " + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("Learning material archives are consistent.")
