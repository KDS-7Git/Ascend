from datetime import date, datetime

import pytest

from ascend.engine.streak import best_streak, compute_streak, logical_date


@pytest.mark.parametrize(
    "days,today,expected",
    [
        ([], 5, 0),
        ([5], 5, 1),
        ([2, 3, 4], 5, 3),
        ([2, 4, 5], 5, 3),
        ([2, 4, 6], 6, 2),
        ([1, 4, 5], 5, 2),
        ([3], 5, 0),
        ([3, 5], 5, 2),  # v1 table's 3 contradicts its algorithm: a freeze adds ZERO.
    ],
)
def test_reference_acceptance(days, today, expected):
    assert (
        compute_streak({date(2026, 11, d) for d in days}, date(2026, 11, today))
        == expected
    )


def test_iso_week_boundary_and_best():
    days = {date(2026, 10, 30), date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 4)}
    assert compute_streak(days, date(2026, 11, 4)) == 4
    assert best_streak(days) == 4


@pytest.mark.parametrize(
    "hour,expected", [(1, date(2026, 10, 31)), (4, date(2026, 11, 1))]
)
def test_rollover(hour, expected):
    assert logical_date(datetime(2026, 11, 1, hour)) == expected


def test_multiple_entries_are_one_day(installed):
    installed.log("I understood why this example works", "Try another example")
    installed.log("I explained the result in my own words", "Continue tomorrow")
    assert installed.stats()["current_streak"] == 1


def test_freezes_can_be_disabled():
    assert (
        compute_streak({date(2026, 11, 3), date(2026, 11, 5)}, date(2026, 11, 5), 0)
        == 1
    )
