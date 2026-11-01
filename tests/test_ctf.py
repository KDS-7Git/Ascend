from datetime import timedelta
import hashlib
import hmac
import json

import pytest

from ascend import timing
from ascend.engine.packs import PackError, dump_toml, parse_pack
from ascend.verifiers.ctf import canonical
from scripts import collect_lab_proof


def bridge(tracker, pack_data, tmp_path, monkeypatch):
    key = "ab" * 32
    monkeypatch.setenv("ASCEND_LAB_SIGNING_KEY", key)
    monkeypatch.setenv("ASCEND_LAB_RECEIPTS_DIR", str(tmp_path))
    pack_data["node"][0]["verify"] = {
        "type": "ctf",
        "provider": "juice-shop",
        "challenge": "loginAdminChallenge",
        "all_of": ["scoreBoardChallenge"],
    }
    tracker.install_pack(dump_toml(pack_data))
    tracker.start_mission("test-pack")
    payload = {
        "provider": "juice-shop",
        "owner": 1,
        "observed_at": tracker.now().isoformat(),
        "solved": ["loginAdminChallenge", "scoreBoardChallenge"],
    }

    def write(value=None, signature=None):
        value = payload if value is None else value
        sig = hmac.new(bytes.fromhex(key), canonical(value), hashlib.sha256).hexdigest()
        (tmp_path / "juice-shop-1.json").write_text(
            json.dumps(
                {"payload": value, "signature": sig if signature is None else signature}
            )
        )

    return payload, write


def test_only_signed_owned_fresh_complete_receipt_rewards(
    tracker, pack_data, tmp_path, monkeypatch
):
    payload, write = bridge(tracker, pack_data, tmp_path, monkeypatch)
    timing.start(tracker, "one", minutes=10)
    for changes in [
        {"owner": 2},
        {"owner": True},
        {"provider": "bandit"},
        {"observed_at": (tracker.now() - timedelta(minutes=6)).isoformat()},
        {"observed_at": (tracker.now() + timedelta(minutes=1)).isoformat()},
        {"observed_at": tracker.now().replace(tzinfo=None).isoformat()},
        {"solved": ["loginAdminChallenge"]},
        {"solved": "loginAdminChallenge scoreBoardChallenge"},
        {"solved": [True]},
    ]:
        write(payload | changes)
        assert not tracker.check("one", confirm=True)["ok"]
        with pytest.raises(ValueError):
            tracker.mark("one", "done")
    write(signature="00" * 32)
    assert not tracker.check("one")["ok"]
    write()
    assert tracker.check("one", confirm=True)["ok"]
    assert timing.summary(tracker)["xp"] == 100
    # An observation is not a historical solve timestamp or a learning note.
    assert tracker.entries() == []
    tracker.check("one", confirm=True)
    assert timing.summary(tracker)["xp"] == 100


@pytest.mark.parametrize("required", ["one", {}, [False], [""]])
def test_ctf_requires_well_formed_challenge_list(pack_data, required):
    pack_data["node"][0]["verify"] = {
        "type": "ctf",
        "provider": "juice-shop",
        "challenge": "scoreBoardChallenge",
        "all_of": required,
    }
    with pytest.raises(PackError):
        parse_pack(dump_toml(pack_data))


def test_collector_key_is_stable_and_private(tmp_path):
    key = collect_lab_proof.initialize(tmp_path)
    assert len(bytes.fromhex(key)) == 32
    assert collect_lab_proof.initialize(tmp_path) == key
    assert (tmp_path / "proofs.env").stat().st_mode & 0o777 == 0o600


def test_bandit_collector_uses_fixed_host_and_validates_identity(tmp_path, monkeypatch):
    calls = []

    def run(args, **kwargs):
        calls.append(args)

        class Result:
            stdout = b"bandit1\n"

        return Result()

    monkeypatch.setattr(collect_lab_proof.subprocess, "run", run)
    assert collect_lab_proof.bandit(0, 1, tmp_path)["solved"] == ["bandit-0"]
    assert calls[0][-1] == "bandit1@bandit.labs.overthewire.org"
    assert "-fNT" in calls[0] and "ClearAllForwardings=yes" in calls[0]
    assert "StrictHostKeyChecking=yes" in calls[0]
    assert calls[1][-2] == "check" and calls[2][-2] == "exit"

    def reject(args, **kwargs):
        if kwargs.get("check"):
            raise collect_lab_proof.subprocess.CalledProcessError(255, args)

    monkeypatch.setattr(collect_lab_proof.subprocess, "run", reject)
    with pytest.raises(collect_lab_proof.subprocess.CalledProcessError):
        collect_lab_proof.bandit(1, 1, tmp_path)
    with pytest.raises(ValueError):
        collect_lab_proof.bandit(33, 1, tmp_path)
