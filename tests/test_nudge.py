from datetime import timedelta
from unittest.mock import patch

from ascend.nudge import NudgeRunner, systemd_units


def test_nudge_stops_after_log(installed, now):
    installed.clock = lambda: now.replace(hour=21, minute=30)
    sent = []
    runner = NudgeRunner(installed, sender=lambda text: sent.append(text))
    assert runner.run()["sent"]
    assert not runner.run()["sent"]
    installed.log("I wrote a clear explanation of my experiment", "Try the next example")
    installed.clock = lambda: now.replace(hour=23, minute=30)
    assert not runner.run()["sent"]
    assert len(sent) == 1


def test_two_nudges_max_and_risk_text(installed, now):
    sent = []
    runner = NudgeRunner(installed, sender=sent.append)
    installed.clock = lambda: now.replace(hour=20)
    assert not runner.run()["sent"]
    installed.clock = lambda: now.replace(hour=21, minute=30)
    assert runner.run()["sent"]
    installed.clock = lambda: now.replace(hour=23, minute=30)
    assert runner.run()["sent"]
    assert not runner.run()["sent"]
    assert len(sent) == 2
    assert "at risk" in sent[0] and "First task" in sent[0]


def test_mission_override(installed, now):
    installed.db.update("missions", "status='active'", nudge_time="18:00")
    installed.clock = lambda: now.replace(hour=18)
    assert NudgeRunner(installed, sender=lambda text: None).run()["sent"]


def test_missing_desktop_is_actionable(installed):
    from ascend.nudge.channels.desktop import send
    with patch("ascend.nudge.channels.desktop.shutil.which", return_value=None):
        try: send("Test notification")
        except ValueError as error: assert "notify-send" in str(error)
        else: assert False, "Missing notification executable must be reported"


def test_units_use_current_profile_and_minute_schedule(tmp_path):
    units = systemd_units(tmp_path, "/some path/python")
    assert "OnCalendar=*-*-* *:*:00" in units["ascend-nudge.timer"]
    assert str(tmp_path) in units["ascend-nudge.service"]
    assert '"/some path/python" -m ascend nudge' in units["ascend-nudge.service"]


def test_failed_send_does_not_consume_slot(installed, now):
    installed.clock = lambda: now.replace(hour=22)
    def fail(text): raise ValueError("Desktop unavailable")
    import pytest
    with pytest.raises(ValueError): NudgeRunner(installed, sender=fail).run()
    assert NudgeRunner(installed, sender=lambda text: None).run()["sent"]
