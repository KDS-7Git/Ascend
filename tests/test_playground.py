"""Activity isolation, evidence privacy, replay safety and cross-client contracts."""

import hashlib
import ipaddress
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from ascend import labs, timing
from ascend.application import Tracker
from ascend.cli import execute, parser
from ascend.engine.packs import dump_toml
from ascend.engine.practice import readiness
from ascend.playground import catalog, fixtures
from ascend.server.app import create_app
from ascend.storage import MIGRATIONS, Database


def key(t, run):
    return json.loads(t.playground.owned(run["id"])["fixture"])["expected"]


def solve(t, id, **kwargs):
    run = t.playground.start(id, deliberate=True, **kwargs)
    return t.playground.submit(
        run["id"],
        key(t, run),
        "I compared independent controls for " + run["id"][:8],
        "Try a changed condition",
    )


def test_completed_side_node_still_offers_short_practice_and_main_path(installed):
    t = installed
    t.mark("small", "done")
    before = deepcopy(t.states("test-pack"))
    today = t.overview(10)
    assert today["next"]["id"] == "one"
    assert today["next"]["estimate"] > 10
    assert today["quick_win"] is None
    assert today["practice"]["activities"]
    solve(t, "request-decisions")
    assert t.overview(10)["practice"]["activities"]
    assert t.states("test-pack") == before


def test_cold_start_completed_or_paused_mission_keeps_practice(installed):
    t = installed
    for node in ("one", "two", "small"):
        t.mark(node, "done")
    for _ in range(2):
        picks = t.playground.recommendations(5)["activities"]
        assert len(picks) >= 2
        assert all(
            a["role"] == "example" and a["environment"] == "browser" for a in picks
        )
        if t.active_mission():
            t.finish_mission("paused")
    assert t.overview(5)["practice"]["activities"]


def test_reward_caps_fresh_variants_and_logical_days(tracker):
    t = tracker
    t.configure("timezone", "Asia/Kolkata")
    t.clock = lambda: datetime(
        2026, 11, 5, 22, 20, tzinfo=timezone.utc
    )  # 03:50 next morning
    results = [
        solve(t, id)
        for id in (
            "request-decisions",
            "request-decisions",
            "address-boundaries",
            "event-filter",
            "copy-check",
        )
    ]
    assert [r["result"]["xp"] for r in results] == [10, 0, 10, 10, 0]
    assert t.xp_totals() == {"track": 0, "practice": 30, "challenge": 0, "total": 30}
    assert results[0]["data"] != results[1]["data"]
    assert len(t.db.rows("activity_runs")) == 5
    assert all(e["mission_id"] is None and e["node_id"] is None for e in t.entries())
    t.clock = lambda: datetime(2026, 11, 5, 22, 31, tzinfo=timezone.utc)
    assert solve(t, "request-decisions")["result"]["xp"] == 10
    assert t.stats()["current_streak"] == 2


def test_explicit_logs_do_not_bind_to_mission_or_duplicate_completion(installed):
    t = installed
    mission, before = t.active_mission(), t.states("test-pack")
    run = t.playground.start("request-change", deliberate=True)
    t.playground.log(
        run["id"],
        "I compared identity state and owner access",
        "Test the changed identity",
        5,
    )
    t.playground.submit(run["id"], key(t, run))
    assert len(t.entries()) == 1
    assert t.entries()[0]["mission_id"] is None
    assert t.entries()[0]["activity_run_id"] == run["id"]
    assert t.active_mission() == mission and t.states("test-pack") == before
    assert t.overview()["resume"] is None
    assert "Playground activity" in t.export() and run["id"] in t.export()


def test_automatic_habit_setting_and_substantive_notes(tracker):
    t = tracker
    t.configure("auto_counts_for_streak", "false")
    result = solve(t, "request-decisions")
    assert not t.entries() and result["result"]["xp"] == 10
    run = t.playground.start("timeline-workspace")
    t.playground.experiment(run["id"], run["work"]["workspace"])
    t.playground.save(run["id"], run["work"])
    assert not t.entries()
    with pytest.raises(ValueError, match="20 characters"):
        t.playground.log(run["id"], "opened it", "later")
    t.playground.log(
        run["id"],
        "Changing the minimum status hides successful events",
        "Compare the full stream",
    )
    assert t.stats()["today_logged"]


@pytest.mark.parametrize("id", ["policy-workspace", "timeline-workspace"])
def test_workspace_save_restart_reset_and_blank_copy(tracker, id):
    t = tracker
    run = t.playground.start(id)
    work = deepcopy(run["work"])
    workspace = work["workspace"]
    if "policy" in workspace:
        workspace["policy"]["admin_write"] = True
    else:
        workspace["minimum_status"] = 500
    observed = t.playground.experiment(run["id"], workspace)["observations"]
    assert observed != run["observations"]
    t.playground.save(run["id"], work)
    other = Tracker(Database(t.db.home))
    try:
        assert other.playground.resume(run["id"])["work"] == work
        copy = other.playground.copy(run["id"], reset=True)
        assert copy["id"] != run["id"] and copy["work"]["workspace"] == run["data"]
        assert other.playground.view(run["id"])["work"] == work
        blank = other.playground.copy(copy["id"], blank=True)
        assert not blank["work"]["workspace"].get(
            "requests", blank["work"]["workspace"].get("events")
        )
        assert not other.entries() and other.xp_totals()["total"] == 0
    finally:
        other.db.close()


def test_hidden_fault_requires_preparation_preserves_copy_and_controls(tracker):
    t = tracker
    run = t.playground.start("policy-workspace")
    with pytest.raises(ValueError, match="example"):
        t.playground.copy(run["id"], fault=True)
    solve(t, "example-access")
    copy = t.playground.copy(run["id"], fault=True)
    assert copy["hidden_fault"] and "fault_rule" not in copy
    assert t.playground.view(run["id"])["work"] == run["work"]
    fixture = json.loads(t.playground.owned(copy["id"])["fixture"])
    assert t.playground.repair(copy["id"], fixture["fault"])["repaired"]
    assert t.playground.view(copy["id"])["observations"] == run["observations"]
    t.playground.end(copy["id"])
    assert t.playground.reveal(copy["id"])["fault_rule"] == fixture["fault"]
    same = t.playground.copy(copy["id"])
    assert same["familiar"]


def test_track_attempt_requires_explicit_switch_and_preserves_receipt(
    tracker, pack_data
):
    t = tracker
    pack_data["node"][0]["verify"] = {"type": "lab", "exercise": "access-policy"}
    t.install_pack(dump_toml(pack_data))
    t.start_mission("test-pack")
    run = labs.start(t, "one")
    clock = t.db.rows("task_sessions")[0]
    t.playground.list()
    assert t.db.rows("task_sessions")[0] == clock
    with pytest.raises(ValueError, match="End scored attempt and switch"):
        t.playground.start("example-access")
    t.playground.start("example-access", end_scored=True)
    ended = t.db.rows("task_sessions")[0]
    assert (
        ended["status"] == "finished"
        and ended["budget_seconds"] == clock["budget_seconds"]
    )
    assert not t.db.rows("xp_awards")
    with pytest.raises(ValueError, match="Save the active Playground"):
        timing.start(t, "small")
    # The old assessment cannot acquire new rewards through practice.
    answers = {r["id"]: labs.access_decision(r)[0] for r in run["data"]["requests"]}
    labs.submit(t, run["id"], answers)
    protected = {
        table: t.db.rows(table)
        for table in (
            "permission_attempts",
            "task_sessions",
            "xp_awards",
            "node_state",
            "lab_runs",
        )
    }
    solve(t, "request-decisions")
    assert all(t.db.rows(table) == rows for table, rows in protected.items())


def test_additive_migration_keeps_existing_profile(installed, remove_playground_schema):
    t = installed
    t.log("I compared the existing project boundaries", "Continue with the next task")
    before = {
        table: t.db.rows(table)
        for table in ("entries", "missions", "node_state", "packs")
    }
    remove_playground_schema(t.db)
    t.db.connection.execute("UPDATE schema_version SET version=7")
    other = Database(t.db.home)
    try:
        assert all(other.rows(table) == rows for table, rows in before.items())
        assert other.connection.execute(
            "SELECT version FROM schema_version"
        ).fetchone()[0] == int(MIGRATIONS[-1].name.split("_")[0])
    finally:
        other.close()


def test_concurrent_submissions_award_and_complete_once(tracker):
    t = tracker
    run = t.playground.start("policy-audit", deliberate=True)
    answers = key(t, run)
    gate = Barrier(2)

    def submit():
        db = Database(t.db.home)
        try:
            other = Tracker(db, t.clock)
            gate.wait(timeout=10)
            return other.playground.submit(run["id"], answers)
        finally:
            db.close()

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert (
        sum(result["result"]["practice_reward"]["newly_awarded"] for result in results)
        == 1
    )
    recorded = deepcopy(results)
    for result in recorded:
        result["result"]["practice_reward"]["newly_awarded"] = False
    assert recorded[0] == recorded[1]
    assert len(t.db.rows("activity_rewards")) == 1 and len(t.entries()) == 1
    assert len(t.db.rows("practice_rewards")) == 1
    assert t.db.rows("practice_rewards")[0]["points"] == 5
    assert solve(t, "policy-audit")["result"]["xp"] == 0
    assert t.playground.submit(run["id"], {}) == recorded[0]


def test_concurrent_track_and_activity_starts_leave_one_foreground(installed):
    t = installed
    gate = Barrier(2)

    def start(kind):
        db = Database(t.db.home)
        try:
            other = Tracker(db, t.clock)
            gate.wait(timeout=10)
            try:
                return (
                    timing.start(other, "one")
                    if kind
                    else other.playground.start("example-access")
                )
            except ValueError:
                return None
        finally:
            db.close()

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(start, [True, False]))
    assert sum(r is not None for r in results) == 1
    assert (
        len(t.db.rows("task_sessions", "status='running'"))
        + len(t.db.rows("activity_runs", "status='active'"))
        == 1
    )


def test_ownership_all_run_and_workspace_actions(tracker):
    t = tracker
    run = t.playground.start("policy-workspace")
    t.db.connection.execute(
        "INSERT INTO users VALUES (2,'other','!disabled','UTC','2026-01-01')"
    )
    other = Tracker(Database(t.db.home, user_id=2))
    try:
        for action in [
            lambda: other.playground.view(run["id"]),
            lambda: other.playground.save(run["id"], run["work"]),
            lambda: other.playground.resume(run["id"]),
            lambda: other.playground.copy(run["id"]),
            lambda: other.playground.experiment(run["id"], run["data"]),
            lambda: other.playground.end(run["id"]),
            lambda: other.playground.reveal(run["id"]),
            lambda: other.playground.submit(run["id"], {}),
            lambda: other.playground.hint(run["id"]),
            lambda: other.playground.log(
                run["id"], "A substantive observation about another workspace", "Next"
            ),
        ]:
            with pytest.raises(ValueError, match="not found"):
                action()
        assert not other.playground.history()
    finally:
        other.db.close()


def test_examples_never_qualify_blind_mysteries_and_transfer_is_specific(tracker):
    t = tracker
    assert all(
        a["role"] == "example" for a in t.playground.recommendations()["activities"]
    )
    example = solve(t, "example-access")
    assert example["result"]["xp"] == 0
    assert readiness(t.playground.evidence())["access"] == "introduced"
    assert not t.playground.detail("desk-17")["recommended_ready"]
    solve(t, "request-decisions")
    assert not t.playground.detail("desk-17")["recommended_ready"]
    solve(t, "request-change")
    assert t.playground.detail("desk-17")["recommended_ready"]
    assert not t.playground.detail("desk-28")["recommended_ready"]
    assert not t.playground.detail("room-63")["recommended_ready"]


def test_study_during_hard_case_requires_ending_the_timed_attempt(tracker):
    t = tracker
    hard = t.playground.start("room-63", deliberate=True)
    t.playground.save(
        hard["id"], {"notes": "Need to compare the clocks", "environment_problem": True}
    )
    original = t.playground.owned(hard["id"])["fixture"]
    assert t.playground.view(hard["id"])["status"] == "active"
    with pytest.raises(ValueError, match="timed Playground challenge"):
        solve(t, "example-timeline")
    t.playground.end(hard["id"])
    solve(t, "example-timeline")
    resumed = t.playground.resume(hard["id"])
    assert resumed["activity"]["difficulty"] == "hard" and resumed["status"] == "ended"
    assert resumed["checks"] == 0 and not resumed["result"]
    assert resumed["work"]["notes"] == "Need to compare the clocks"
    assert t.playground.owned(hard["id"])["fixture"] == original
    assert not any(e["outcome"] == "needs-practice" for e in t.playground.evidence())


@pytest.mark.parametrize("id", ["desk-17", "desk-28", "room-41", "room-63"])
def test_mystery_privacy_evidence_reveal_and_exhaustion(tracker, id):
    t = tracker
    first = t.playground.start(id, deliberate=True)
    assert not first["familiar"]
    for forbidden in (
        "expected",
        "solution",
        "debrief",
        "fixture_key",
        "variant",
        "reward_key",
        "family",
    ):
        assert forbidden not in first and forbidden not in first["activity"]
    with pytest.raises(ValueError, match="every evidence"):
        t.playground.submit(first["id"], {"conclusion": "anything"})
    with pytest.raises(ValueError, match="Solve or explicitly end"):
        t.playground.reveal(first["id"])
    if first["hints_available"]:
        assert t.playground.hint(first["id"])["hint_text"]
    else:
        with pytest.raises(ValueError, match="no hints"):
            t.playground.hint(first["id"])
    t.playground.end(first["id"])
    revealed = t.playground.reveal(first["id"])
    assert revealed["solution"]
    assert t.playground.submit(first["id"], key(t, first))["status"] == "ended"
    for _ in range(2):
        run = solve(t, id)
        if run["kind"] == "challenge":
            assert run["result"]["xp"] == 0
    repeat = t.playground.start(id, deliberate=True)
    assert repeat["familiar"]


def test_limited_hint_does_not_reduce_first_solve_xp(tracker):
    t = tracker
    run = t.playground.start("room-41", deliberate=True)
    t.playground.hint(run["id"])
    solved = t.playground.submit(run["id"], key(t, run))
    assert solved["result"]["assistance"] == "assisted"
    assert solved["result"]["xp"] == 50
    assert not any(e["independent"] for e in t.playground.evidence())


def test_selection_filters_bookmarks_and_review_without_due_items(tracker):
    t = tracker
    assert not t.playground.list(minutes=5, environment="external")["activities"]
    empty = t.playground.list(minutes=5, topic="subnet")
    assert all(a["minutes"] <= 5 for a in empty["activities"])
    t.playground.bookmark("example-access")
    assert [a["id"] for a in t.playground.list(bookmarked=True)["activities"]] == [
        "example-access"
    ]
    solve(t, "request-change")
    t.clock = lambda: datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
    due = t.playground.recommendations()
    assert due["review"]["access"]["due"]
    solve(t, "request-change")
    assert t.playground.recommendations()["activities"]


def test_cli_and_http_share_the_same_run_contract(tmp_path):
    client = TestClient(create_app(tmp_path, scheduler=False))
    assert client.get("/api/playground").json()["activities"]
    assert client.post("/api/command", json={"argv": ["practice", "10"]}).json()[
        "activities"
    ]
    run = client.post(
        "/api/command",
        json={"argv": ["playground", "start", "request-decisions", "--deliberate"]},
    ).json()
    assert "id" in run
    t = Tracker(Database(tmp_path))
    try:
        result = client.post(
            f"/api/playground/runs/{run['id']}/submit", json={"data": key(t, run)}
        )
        assert result.status_code == 200 and result.json()["result"]["xp"] == 10
        history = execute(t, parser().parse_args(["playground", "history"]))
        assert history[0]["status"] == "passed"
        assert client.get("/api/stats").json()["xp"]["practice"] == 10
        assert client.get("/api/me?minutes=10").json()["practice"]["activities"]
        assert (
            client.post(
                f"/api/playground/runs/{run['id']}/save",
                json={"data": {"notes": "<script>alert(1)</script>"}},
            ).status_code
            == 200
        )
        assert (
            client.get(
                "/api/playground/recommendations?minutes=5&environment=external"
            ).json()["activities"]
            == []
        )
    finally:
        t.db.close()


@pytest.mark.parametrize("iteration", range(15))
def test_generated_evidence_checks_against_independent_calculation(now, iteration):
    # Check generator truth, not just the evaluator accepting its own key.
    subnet = fixtures.generate(catalog.get("address-boundaries"), now)
    interface = ipaddress.ip_interface(subnet["public"]["data"]["interface"])
    assert subnet["expected"] == {
        "network": str(interface.network),
        "broadcast": str(interface.network.broadcast_address),
        "usable_hosts": interface.network.num_addresses - 2,
    }
    policy = fixtures.generate(catalog.get("request-change"), now)
    for request in policy["public"]["data"]["requests"]:
        allowed = request["enabled"] and (
            request["caller"] == request["owner"]
            or request["role"] == "admin"
            and request["action"] == "read"
        )
        assert policy["expected"][request["id"]] == allowed
    log = fixtures.generate(catalog.get("event-compare"), now)
    data = log["public"]["data"]
    matching = [
        r
        for r in data["events"]
        if r["marker"] == data["marker"] and r["status"] >= 400
    ]
    assert log["expected"]["errors"] == len(matching)
    assert log["expected"]["changed"] == len([r for r in matching if r["id"] != "e1"])
    integrity = fixtures.generate(catalog.get("byte-change"), now)
    data = integrity["public"]["data"]
    assert (
        integrity["expected"]["copy_sha256"]
        == hashlib.sha256(data["copy_content"].encode()).hexdigest()
    )
    assert integrity["expected"]["changed_matches"] == (
        data["changed_copy"] == data["trusted_content"]
    )
    timeline = fixtures.generate(catalog.get("event-order"), now)
    times = sorted(
        datetime.fromisoformat(e["time"])
        for e in timeline["public"]["data"]["events"]
        if e["status"] == "failure"
    )
    assert timeline["expected"]["within_minute"] == (
        len(times) >= 5 and times[-1] - times[0] <= timedelta(seconds=60)
    )


@pytest.mark.parametrize("variant", range(3))
def test_authored_mystery_contrasts_and_controls(now, variant):
    mini = fixtures.generate(catalog.get("desk-17"), now, variant)
    request = next(r for r in mini["public"]["data"]["requests"] if r["id"] == "r2")
    request = request | {"action": "read"}
    assert mini["expected"]["prediction"] == labs.access_decision(request)[0]
    dashboard = fixtures.generate(catalog.get("desk-28"), now, variant)
    events = deepcopy(dashboard["public"]["data"]["events"])
    events[0]["status"] = 503
    assert dashboard["expected"]["prediction"] == sum(
        e["marker"] == "job" and e["status"] >= 400 for e in events
    )
    delivery = fixtures.generate(catalog.get("room-41"), now, variant)
    job = delivery["public"]["data"]["jobs"][0]
    assert delivery["expected"]["credential_only"] == (
        job["approved"] and job["team"] == job["destination_team"]
    )
    assert delivery["expected"]["destination_only"] == (
        job["approved"] and job["credential_valid"]
    )
    incident = fixtures.generate(catalog.get("room-63"), now, variant)
    data = incident["public"]["data"]
    assert incident["expected"]["manifest_match"] == (
        data["archive_capture"]["sha256"] == data["trusted_manifest"]["sha256"]
    )
    assert incident["expected"]["transit_change"] == (
        data["archive_capture"]["sha256"] != data["export_capture"]["sha256"]
    )
    assert len(incident["expected"]) >= 12


def test_all_catalog_activities_have_public_fields_and_evaluable_rubrics(now):
    assert (
        len(
            [
                a
                for a in catalog.CATALOG
                if a["kind"] == "quick" and a["role"] != "example"
            ]
        )
        >= 12
    )
    assert len([a for a in catalog.CATALOG if a["kind"] == "challenge"]) >= 6
    for item in catalog.CATALOG:
        fixture = fixtures.generate(item, now)
        assert set(fixture["public"]["fields"]) == set(fixture["expected"])
        assert fixtures.evaluate(fixture, fixture["expected"])
        assert item["minutes"] >= 5
        assert "private" not in json.dumps(catalog.public(item))


@pytest.mark.parametrize("track_first", [True, False])
def test_shared_source_reward_identity_prevents_double_awards(
    tracker, pack_data, monkeypatch, track_first
):
    t = tracker
    pack_data["node"][0]["verify"] = {"type": "lab", "exercise": "access-policy"}
    t.install_pack(dump_toml(pack_data))
    t.start_mission("test-pack")
    alias = deepcopy(catalog.get("policy-audit"))
    alias["id"] = "renamed-audit"
    alias["source_node"] = "test-pack:one"
    alias["reward_key"] = "a-cosmetic-renaming-cannot-mint-an-award"
    monkeypatch.setattr(catalog, "CATALOG", [*catalog.CATALOG, alias])

    def track_solve():
        run = labs.start(t, "one")
        labs.submit(
            t,
            run["id"],
            {r["id"]: labs.access_decision(r)[0] for r in run["data"]["requests"]},
        )

    if track_first:
        track_solve()
        assert solve(t, alias["id"])["result"]["xp"] == 0
        assert t.xp_totals()["total"] == 100
    else:
        assert solve(t, alias["id"])["result"]["xp"] == 25
        track_solve()
        assert t.xp_totals()["total"] == 25
    assert t.states("test-pack")["one"]["status"] == "done"


def test_cosmetic_time_and_order_changes_do_not_create_fresh_evidence(now):
    item = catalog.get("event-order")
    original = fixtures.generate(item, now)
    shifted = deepcopy(original)
    shifted["public"]["data"]["events"].reverse()
    for event in shifted["public"]["data"]["events"]:
        event["time"] = (
            datetime.fromisoformat(event["time"]) + timedelta(days=1)
        ).isoformat()
    assert fixtures.fixture_key(item, original, 0) == fixtures.fixture_key(
        item, shifted, 0
    )


def test_malformed_workspace_requests_return_validation_errors(tracker):
    t = tracker
    run = t.playground.start("policy-workspace")
    workspace = deepcopy(run["data"])
    workspace["requests"][0]["role"] = ["admin"]
    with pytest.raises(ValueError, match="Each request"):
        t.playground.experiment(run["id"], workspace)
    solve(t, "example-access")
    faulty = t.playground.copy(run["id"], fault=True)
    with pytest.raises(ValueError, match="Policy needs"):
        t.playground.experiment(faulty["id"], {})
