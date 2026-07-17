"""
Tests for the pure "math brain" functions in skz_countdown_pkg/logic.py.

These don't open any window — they just check that numbers in produce the
right numbers out. Run them with: pytest
"""

import os
import random
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Let this test file find the skz_countdown_pkg package without needing the
# app "installed" — it just adds the project's home folder to the search path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skz_countdown_pkg.logic import (
    local_display_dt, milestones_crossed, split_remaining,
)


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


def test_split_remaining_roundtrip_always_adds_back_up():
    # A "property test": no matter what total we hand in, splitting it into
    # weeks/days/hours/minutes/seconds and adding those pieces BACK together
    # should always land exactly on the number we started with — and each
    # piece should stay inside its own sensible range (you'd never want to
    # see "26 hours" on the HOURS box).
    rng = random.Random(1234)   # a fixed seed = the same "random" values
    interesting_values = [
        0, 1, 59, 60, 61, 3599, 3600, 3601,
        86399, 86400, 86401, 604799, 604800, 604801,
    ]
    sampled_values = [rng.randint(0, 50_000_000) for _ in range(300)]

    for total in interesting_values + sampled_values:
        weeks, days, hours, minutes, seconds = split_remaining(total)
        rebuilt = (weeks * 7 * 24 * 3600) + (days * 24 * 3600) \
            + (hours * 3600) + (minutes * 60) + seconds
        assert rebuilt == total
        assert 0 <= days < 7
        assert 0 <= hours < 24
        assert 0 <= minutes < 60
        assert 0 <= seconds < 60


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


# ---------------- local_display_dt (the daylight-saving fix) ----------------
# The bug this guards against: converting a future release into "your local
# time" using TODAY's offset instead of the offset that's actually in effect
# ON THE RELEASE DATE. New York, for example, is UTC-4 in summer (EDT) but
# UTC-5 in winter (EST) — reusing one of those offsets for the other season
# silently shifts the displayed time (and sometimes the whole date) by an
# hour. These tests use an explicit zone name (not the machine's own
# timezone) so the result is exactly predictable no matter where the test
# happens to run.

def test_local_display_dt_summer_release_is_edt_in_new_york():
    summer_release = datetime(2026, 8, 7, 13, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    ny = local_display_dt(summer_release, "America/New_York")
    assert ny.strftime("%Z") == "EDT"
    assert ny.utcoffset().total_seconds() == -4 * 3600


def test_local_display_dt_winter_release_is_est_in_new_york():
    winter_release = datetime(2026, 12, 25, 9, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    ny = local_display_dt(winter_release, "America/New_York")
    assert ny.strftime("%Z") == "EST"
    assert ny.utcoffset().total_seconds() == -5 * 3600


def test_local_display_dt_matches_direct_zoneinfo_conversion():
    # Check every season of the year, not just one — this is the same
    # comparison used to hand-verify the fix before writing it down here.
    for month in (1, 4, 7, 10):
        release = datetime(2026, month, 15, 12, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        expected = release.astimezone(ZoneInfo("America/New_York"))
        actual = local_display_dt(release, "America/New_York")
        assert actual == expected


def test_local_display_dt_default_uses_system_timezone():
    # With no zone_name given, it should behave exactly like the plain
    # astimezone() the rest of the app relies on for "my own computer's
    # timezone" — just resolved fresh each call instead of cached once.
    moment = datetime(2026, 6, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
    assert local_display_dt(moment) == moment.astimezone()
