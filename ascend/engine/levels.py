from ascend.engine.packs import Pack


def open_levels(pack: Pack, finished: set[str], overrides=frozenset()):
    opened, prev_complete = set(overrides), True
    for level in pack.levels:
        if level.lane == "side":
            opened.add(level.id)
            continue
        if prev_complete or not level.gate:
            opened.add(level.id)
        nodes = [n for n in pack.nodes if n.level == level.id]
        tested = [n for n in nodes if n.milestone] or nodes
        prev_complete = all(n.id in finished for n in tested)
    return opened


def next_nodes(pack: Pack, state: dict, max_minutes=None, overrides=frozenset()):
    finished = {nid for nid, status in state.items() if status in {"done", "skipped"}}
    opened = open_levels(pack, finished, overrides)
    return [
        n
        for n in pack.nodes
        if n.id not in finished
        and n.level in opened
        and all(r in finished for r in n.needs)
        and (max_minutes is None or n.estimate <= max_minutes)
    ]
