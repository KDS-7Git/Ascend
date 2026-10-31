"""Small checksum-pinned pack registry and explicit resource link checks."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ascend.engine.packs import parse_pack


def community_root():
    root = Path(__file__).resolve().parents[1] / "packs/community"
    return root if root.is_dir() else Path(__file__).parent / "community"


def _download(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Registry URLs must be http(s) without embedded credentials")
    try:
        with urlopen(Request(url, headers={"User-Agent": "Ascend/0.1"}), timeout=10) as response:
            content = response.read(2_000_001)
        if len(content) > 2_000_000: raise ValueError("Registry download exceeds 2 MB")
        return content
    except (URLError, OSError): raise ValueError("Registry download failed") from None


def registry_entries(url=None):
    try:
        raw = json.loads(_download(url)) if url else json.loads((community_root() / "registry.json").read_text())
        entries, seen = raw["packs"], set()
        for entry in entries:
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", entry["id"]) or entry["id"] in seen: raise ValueError("Invalid or duplicate registry ID")
            if not re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]): raise ValueError("Registry requires SHA-256 checksums")
            seen.add(entry["id"])
        return entries
    except (KeyError, TypeError, json.JSONDecodeError): raise ValueError("Invalid registry document") from None


def fetch_pack(pack_id, registry_url):
    entry = next((e for e in registry_entries(registry_url) if e["id"] == pack_id), None)
    if not entry: raise ValueError("Pack is not in the configured registry")
    data = _download(entry["url"])
    if hashlib.sha256(data).hexdigest() != entry["sha256"]: raise ValueError("Pack checksum mismatch")
    text = data.decode("utf-8")
    if parse_pack(text).id != pack_id: raise ValueError("Registry ID does not match the pack")
    return text


def check_link(url):
    for method in ("HEAD", "GET"):
        try:
            with urlopen(Request(url, method=method, headers={"User-Agent": "Mozilla/5.0 (compatible; Ascend/0.1 link checker)"}), timeout=10) as response:
                return {"url": url, "status": response.status, "ok": 200 <= response.status < 400}
        except HTTPError as error:
            if error.code in {404, 405, 501} and method == "HEAD": continue
            return {"url": url, "status": error.code, "ok": False, "reason": "Access restricted" if error.code in {401, 403, 429} else "HTTP error"}
        except (URLError, OSError, ValueError): return {"url": url, "status": None, "ok": False, "reason": "Unreachable"}


def check_links(pack):
    urls = list(dict.fromkeys(node.resource for node in pack.nodes))
    with ThreadPoolExecutor(max_workers=4) as pool: return list(pool.map(check_link, urls))
