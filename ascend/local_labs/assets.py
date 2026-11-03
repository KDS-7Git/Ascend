"""Bounded, immutable downloads; no repository hooks or arbitrary archive extraction."""

import hashlib
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path, value):
    import json

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


class AssetStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def fetch(self, asset):
        size, sha = asset["bytes"], asset["sha256"]
        target = self.root / sha
        if target.is_symlink():
            raise ValueError("Cache object is a symlink")
        if target.exists():
            if target.stat().st_size == size and digest(target) == sha:
                os.utime(target, None)
                return target, 0
            target.unlink()  # Only this content-addressed object, never saved work.
        if shutil.disk_usage(self.root).free < size + 1024 * 1024:
            raise ValueError("Insufficient disk space for this download")
        if urlparse(asset["url"]).scheme != "https":
            raise ValueError("Reviewed downloads must use HTTPS")
        fd, tmp = tempfile.mkstemp(prefix=".part-", dir=self.root)
        count, hasher = 0, hashlib.sha256()
        try:
            req = Request(asset["url"], headers={"User-Agent": "Ascend-local-labs/1"})
            with os.fdopen(fd, "wb") as stream, urlopen(req, timeout=30) as source:
                if urlparse(source.url).scheme != "https":
                    raise ValueError("Insecure download redirect")
                while block := source.read(min(65536, size - count + 1)):
                    count += len(block)
                    if count > size:
                        raise ValueError("Download exceeds its reviewed size")
                    hasher.update(block)
                    stream.write(block)
                stream.flush()
                os.fsync(stream.fileno())
            if count != size or hasher.hexdigest() != sha:
                raise ValueError("Download size or SHA-256 mismatch")
            os.replace(tmp, target)
            return target, count
        finally:
            Path(tmp).unlink(missing_ok=True)

    def selected_zip(self, archive, asset, destination):
        """Write one explicitly named ordinary member; never call extractall."""
        with zipfile.ZipFile(archive) as source:
            entries = source.infolist()
            if len(entries) != 1 or entries[0].filename != asset["member"]:
                raise ValueError("Unexpected archive contents")
            info = entries[0]
            mode = info.external_attr >> 16
            if (info.is_dir() or stat.S_ISLNK(mode) or
                    (stat.S_IFMT(mode) and not stat.S_ISREG(mode)) or
                    info.file_size != asset["expanded_bytes"]):
                raise ValueError("Unsupported archive member")
            with source.open(info) as stream:
                content = stream.read(asset["expanded_bytes"] + 1)
            if len(content) != asset["expanded_bytes"] or hashlib.sha256(content).hexdigest() != asset["expanded_sha256"]:
                raise ValueError("Expanded artifact hash mismatch")
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if destination.is_symlink():
                raise ValueError("Evidence destination is a symlink")
            destination.write_bytes(content)
            return destination

    def prune(self, protected, budget_bytes):
        if type(budget_bytes) is not int or budget_bytes < 0:
            raise ValueError("Cache budget must be a non-negative byte count")
        files = [p for p in self.root.iterdir() if p.is_file() and not p.is_symlink()
                 and (re.fullmatch(r"[0-9a-f]{64}", p.name) or p.name.startswith(".part-"))]
        total = sum(p.stat().st_size for p in files)
        removed = []
        for path in sorted(files, key=lambda p: p.stat().st_mtime):
            if path.name in protected or (total <= budget_bytes and not path.name.startswith(".part-")):
                continue
            size = path.stat().st_size
            path.unlink()
            total -= size
            removed.append(path.name)
        return {"cache_bytes": total, "removed": removed, "protected_objects": len(protected),
                "saved_work_removed": False, "provider_images_removed": False}
