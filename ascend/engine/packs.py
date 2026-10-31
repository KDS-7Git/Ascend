"""TOML parsing and validation, independent of the filesystem."""
from dataclasses import dataclass, field
import json
import re
import tomllib
from urllib.parse import urlparse

SIZE_MIN = {"S": 30, "M": 120, "L": 240}
BUILTINS = {"manual", "file", "command"}
IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PackError(ValueError):
    pass


@dataclass(frozen=True)
class Level:
    id: str
    title: str
    lane: str = "main"
    gate: bool = True


@dataclass(frozen=True)
class Node:
    id: str
    level: str
    title: str
    size: str
    done_when: str
    resource: str
    needs: tuple[str, ...] = ()
    verify: dict = field(default_factory=lambda: {"type": "manual"})
    milestone: bool = False
    auto_complete: bool = False
    minutes: int | None = None

    @property
    def estimate(self):
        return self.minutes or SIZE_MIN[self.size]


@dataclass(frozen=True)
class Pack:
    id: str
    title: str
    kind: str
    version: int
    source: str
    reviewed: bool
    vars: dict
    levels: tuple[Level, ...]
    nodes: tuple[Node, ...]


def substitute(value, variables):
    if isinstance(value, str):
        return re.sub(r"\{([A-Za-z_][A-Za-z_0-9]*)\}", lambda m: str(variables.get(m[1], m[0])), value)
    if isinstance(value, dict):
        return {k: substitute(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, variables) for v in value]
    return value


def _required(data, name):
    value = data.get(name)
    if not isinstance(value, str) or not value.strip():
        raise PackError(f"Missing or invalid {name}")
    return value


def _identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise PackError("IDs must use lowercase letters, numbers and hyphens")
    return value


def parse_pack(text: str, variables=None, allowed_verifiers=None) -> Pack:
    try:
        raw = tomllib.loads(text)
        meta = raw.get("pack", {})
        pid = _identifier(_required(meta, "id"))
        if meta.get("kind") not in {"project", "proficiency"}:
            raise PackError("pack.kind must be project or proficiency")
        if type(meta.get("version")) is not int or meta["version"] < 1:
            raise PackError("pack.version must be a positive integer")
        if meta.get("source", "human") not in {"human", "ai-draft", "imported"}:
            raise PackError("Unknown pack.source")
        vars_ = {**raw.get("vars", {}), **(variables or {})}
        levels, seen = [], set()
        for lv in raw.get("level", []):
            lid = _identifier(_required(lv, "id"))
            if lid in seen: raise PackError(f"Duplicate level id: {lid}")
            seen.add(lid)
            if lv.get("lane", "main") not in {"main", "side"}: raise PackError("Invalid lane")
            if type(lv.get("gate", True)) is not bool: raise PackError("gate must be boolean")
            levels.append(Level(lid, _required(lv, "title"), lv.get("lane", "main"), lv.get("gate", True)))
        if not any(lv.lane == "main" for lv in levels): raise PackError("At least one main level is required")
        nodes, ids = [], set()
        for original in raw.get("node", []):
            base_id = _identifier(_required(original, "id"))
            series = original.get("series")
            if series:
                start, stop = series.get("from"), series.get("to")
                if type(start) is not int or type(stop) is not int or start < 0 or stop < start or stop - start > 10000:
                    raise PackError("Invalid series bounds")
                numbers = range(start, stop + 1)
            else:
                numbers = [None]
            for number in numbers:
                n = substitute(original, {**vars_, **({"n": number, "next": number + 1} if number is not None else {})})
                nid = f"{base_id}-{number}" if series else base_id
                if nid in ids: raise PackError(f"Duplicate node id: {nid}")
                ids.add(nid)
                if n.get("level") not in seen: raise PackError(f"Unknown level for {nid}")
                if n.get("size") not in SIZE_MIN: raise PackError(f"Invalid size for {nid}")
                done_when = _required(n, "done_when")
                if len(done_when.strip()) < 15: raise PackError(f"done_when too short for {nid}")
                url = urlparse(_required(n, "resource"))
                if url.scheme not in {"http", "https"} or not url.netloc: raise PackError(f"Invalid resource URL for {nid}")
                needs = n.get("needs", [])
                if not isinstance(needs, list) or any(not isinstance(v, str) for v in needs): raise PackError("needs must be a list of IDs")
                if series and number > start: needs = [f"{base_id}-{number - 1}"]
                verify = original.get("verify", {"type": "manual"})
                vtype = verify.get("type", "manual")
                if vtype not in (allowed_verifiers or BUILTINS): raise PackError(f"Unknown verify.type: {vtype}")
                if vtype == "file": _required(verify, "path")
                if vtype == "command": _required(verify, "cmd")
                minutes = n.get("minutes")
                if minutes is not None and (type(minutes) is not int or not 1 <= minutes <= SIZE_MIN[n["size"]]):
                    raise PackError("minutes must be positive and within the size bound")
                for key in ("milestone", "auto_complete"):
                    if type(n.get(key, False)) is not bool: raise PackError(f"{key} must be boolean")
                nodes.append(Node(nid, n["level"], _required(n, "title"), n["size"], done_when, n["resource"], tuple(needs),
                                  substitute(verify, {"n": number, "next": number + 1} if number is not None else {}),
                                  n.get("milestone", False), n.get("auto_complete", False), minutes))
        if not nodes: raise PackError("At least one node is required")
        graph = {n.id: n.needs for n in nodes}
        visiting, visited = set(), set()
        def visit(nid):
            if nid not in graph: raise PackError(f"Unknown prerequisite: {nid}")
            if nid in visiting: raise PackError("Prerequisite cycle detected")
            if nid in visited: return
            visiting.add(nid)
            for req in graph[nid]: visit(req)
            visiting.remove(nid); visited.add(nid)
        for nid in graph: visit(nid)
        if meta["kind"] == "proficiency":
            mains = [lv for lv in levels if lv.lane == "main"]
            if not 8 <= len(mains) <= 15: raise PackError("Proficiency packs need 8–15 main levels")
            for lv in mains:
                milestones = [n for n in nodes if n.level == lv.id and n.milestone]
                if not milestones: raise PackError(f"Missing milestone in {lv.id}")
                if any(n.size == "S" for n in milestones): raise PackError("Proficiency milestones must be M or L")
        return Pack(pid, _required(meta, "title"), meta["kind"], meta["version"], meta.get("source", "human"),
                    bool(meta.get("reviewed", False)), vars_, tuple(levels), tuple(nodes))
    except (tomllib.TOMLDecodeError, KeyError, TypeError, AttributeError, RecursionError) as error:
        raise PackError(f"Invalid pack: {error}") from error


def dump_toml(data):
    """Serialize the small, explicit TOML subset used by packs."""
    def value(v):
        if isinstance(v, bool): return "true" if v else "false"
        if isinstance(v, str): return json.dumps(v, ensure_ascii=False)
        if isinstance(v, (int, float)): return str(v)
        if isinstance(v, (list, tuple)): return "[" + ", ".join(value(x) for x in v) + "]"
        if isinstance(v, dict): return "{ " + ", ".join(f"{json.dumps(k)} = {value(x)}" for k, x in v.items()) + " }"
        raise ValueError("Unsupported TOML value")
    lines = []
    for key, section in data.items():
        sections = section if isinstance(section, list) else [section]
        for item in sections:
            lines.append(f"[[{key}]]" if isinstance(section, list) else f"[{key}]")
            lines.extend(f"{json.dumps(k)} = {value(v)}" for k, v in item.items())
            lines.append("")
    return "\n".join(lines)
