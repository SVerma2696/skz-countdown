"""
Tests for the pure "math brain" functions in skz_countdown_pkg/logic.py.

These don't open any window — they just check that numbers in produce the
right numbers out. Run them with: pytest
"""

import os
import sys

# Let this test file find the skz_countdown_pkg package without needing the
# app "installed" — it just adds the project's home folder to the search path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skz_countdown_pkg.logic import split_remaining, milestones_crossed


# ---------------- split_remaining ----------------

def test_split_remaining_zero():
    assert split_remaining(0) == (0, 0, 0, 0, 0)


def test_split_remaining_plain_seconds():
    assert split_remaining(45) == (0, 0, 0, 0, 45)


def test_split_remaining_exact_week():
    seconds_in_a_week = 7 * 24 * 3600
    assert split_remaining(seconds_in_a_week) == (1, 0, 0, 0, 0)


def test_split_remaining_exact_day():
    seconds_in_a_day = 24 * 3600
    assert split_remaining(seconds_in_a_day) == (0, 1, 0, 0, 0)


def test_split_remaining_exact_hour():
    assert split_remaining(3600) == (0, 0, 1, 0, 0)


def test_split_remaining_mixed():
    # 2 weeks, 3 days, 4 hours, 5 minutes, 6 seconds, added up by hand.
    total = (2 * 7 * 24 * 3600) + (3 * 24 * 3600) + (4 * 3600) + (5 * 60) + 6
    assert split_remaining(total) == (2, 3, 4, 5, 6)


# ---------------- milestones_crossed ----------------

_TEST_MILESTONES = [
    ("notify_1w", "1 week to go", 7 * 24 * 3600),
    ("notify_1d", "1 day to go", 24 * 3600),
    ("notify_1h", "1 hour to go", 3600),
    ("notify_release", "IT'S OUT!", 0),
]

_ALL_ON = {
    "notify_1w": True, "notify_1d": True,
    "notify_1h": True, "notify_release": True,
}


def test_nothing_crossed_far_from_release():
    result = milestones_crossed(
        remaining=30 * 24 * 3600, fired=set(), settings=_ALL_ON,
        milestones=_TEST_MILESTONES)
    assert result == []


def test_one_week_milestone_crosses_alone():
    result = milestones_crossed(
        remaining=7 * 24 * 3600, fired=set(), settings=_ALL_ON,
        milestones=_TEST_MILESTONES)
    assert [key for key, _label, _secs in result] == ["notify_1w"]


def test_already_fired_milestone_is_not_returned_again():
    result = milestones_crossed(
        remaining=7 * 24 * 3600, fired={"notify_1w"}, settings=_ALL_ON,
        milestones=_TEST_MILESTONES)
    assert result == []


def test_disabled_milestone_is_skipped():
    settings = dict(_ALL_ON)
    settings["notify_1w"] = False
    result = milestones_crossed(
        remaining=7 * 24 * 3600, fired=set(), settings=settings,
        milestones=_TEST_MILESTONES)
    assert result == []


def test_multiple_milestones_crossed_at_once():
    # Like opening the app for the first time after the album already
    # dropped: every milestone should be "newly crossed" together.
    result = milestones_crossed(
        remaining=-100, fired=set(), settings=_ALL_ON,
        milestones=_TEST_MILESTONES)
    assert [key for key, _label, _secs in result] == [
        "notify_1w", "notify_1d", "notify_1h", "notify_release",
    ]


def test_release_milestone_only_at_or_past_zero():
    just_before = milestones_crossed(
        remaining=1, fired=set(), settings=_ALL_ON,
        milestones=_TEST_MILESTONES)
    assert "notify_release" not in [key for key, _l, _s in just_before]

    at_release = milestones_crossed(
        remaining=0, fired=set(), settings=_ALL_ON,
        milestones=_TEST_MILESTONES)
    assert "notify_release" in [key for key, _l, _s in at_release]
