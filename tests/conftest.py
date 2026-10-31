from datetime import datetime, timezone

import pytest

from ascend.application import Tracker
from ascend.storage import Database


@pytest.fixture
def now():
    return datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


@pytest.fixture
def tracker(tmp_path, now):
    return Tracker(Database(tmp_path), clock=lambda: now)


@pytest.fixture
def pack_data():
    return {
        "pack": {"id": "test-pack", "title": "Test pack", "kind": "project", "version": 1,
                 "source": "human", "reviewed": True},
        "vars": {},
        "level": [{"id": "first", "title": "First"}, {"id": "second", "title": "Second"},
                  {"id": "anytime", "title": "Anytime", "lane": "side"}],
        "node": [
            {"id": "one", "level": "first", "title": "First task", "size": "M", "needs": [],
             "done_when": "An explanation saved in my own words", "resource": "https://docs.python.org/3/"},
            {"id": "two", "level": "second", "title": "Second task", "size": "M", "needs": [],
             "done_when": "A working program and written explanation", "resource": "https://docs.python.org/3/"},
            {"id": "small", "level": "anytime", "title": "Small task", "size": "S", "needs": [],
             "done_when": "One small example with a written explanation", "resource": "https://docs.python.org/3/"},
        ],
    }


@pytest.fixture
def installed(tracker, pack_data):
    from ascend.engine.packs import dump_toml
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    return tracker
