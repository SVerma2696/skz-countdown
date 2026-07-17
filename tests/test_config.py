"""
Tests for how skz_countdown_pkg/config.py reads release.json and falls back
to safe defaults when that file is missing, broken, or just wrong — a typo
in a config file should NEVER be able to crash the whole app.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import skz_countdown_pkg.config as config
from skz_countdown_pkg.config import DEFAULT_RELEASE, _release_datetime


# ---------------- _release_datetime: turning text into a real moment ----------------

def _default_moment():
    return _release_datetime(DEFAULT_RELEASE)


def test_valid_default_data_parses_correctly():
    dt = _default_moment()
    assert (dt.year, dt.month, dt.day) == (2026, 8, 7)
    assert (dt.hour, dt.minute, dt.second) == (13, 0, 0)
    assert dt.tzinfo.key == "Asia/Seoul"


def test_valid_custom_release_parses_correctly():
    data = dict(DEFAULT_RELEASE)
    data.update({
        "release_date": "2026-12-25",
        "release_time": "09:30:00",
        "release_timezone": "America/New_York",
    })
    dt = _release_datetime(data)
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == \
        (2026, 12, 25, 9, 30)
    assert dt.tzinfo.key == "America/New_York"


def test_typo_timezone_falls_back_to_default():
    data = dict(DEFAULT_RELEASE)
    data["release_timezone"] = "Asia/Seol"   # typo — not a real zone name
    assert _release_datetime(data) == _default_moment()


def test_garbage_date_falls_back_to_default():
    data = dict(DEFAULT_RELEASE)
    data["release_date"] = "not-a-date"
    assert _release_datetime(data) == _default_moment()


def test_february_30th_falls_back_to_default():
    # A real-looking date that doesn't actually exist on any calendar.
    data = dict(DEFAULT_RELEASE)
    data["release_date"] = "2026-02-30"
    assert _release_datetime(data) == _default_moment()


def test_garbage_time_falls_back_to_default():
    data = dict(DEFAULT_RELEASE)
    data["release_time"] = "25:99:99"
    assert _release_datetime(data) == _default_moment()


def test_missing_keys_fall_back_to_default():
    # Only one field present — like someone editing release.json and only
    # meaning to change the album name, not realizing they deleted the rest.
    data = {"album_name": "Some Other Comeback"}
    assert _release_datetime(data) == _default_moment()


# ---------------- load_release_config: the search order ----------------

def test_search_order_first_valid_file_wins(tmp_path, monkeypatch):
    good = tmp_path / "release.json"
    good.write_text(json.dumps({"album_name": "TEST ALBUM"}), encoding="utf-8")
    missing = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(
        config, "_release_json_search_paths",
        lambda: [str(missing), str(good)])

    data = config.load_release_config()
    assert data["album_name"] == "TEST ALBUM"
    # Everything NOT overridden by the found file still comes from the
    # built-in defaults — a partial release.json shouldn't blank out the
    # rest of the app's config.
    assert data["release_timezone"] == DEFAULT_RELEASE["release_timezone"]


def test_search_order_skips_broken_json_and_keeps_looking(tmp_path, monkeypatch):
    broken = tmp_path / "broken.json"
    broken.write_text("{this is not valid json", encoding="utf-8")
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"album_name": "GOOD ALBUM"}), encoding="utf-8")
    monkeypatch.setattr(
        config, "_release_json_search_paths",
        lambda: [str(broken), str(good)])

    data = config.load_release_config()
    assert data["album_name"] == "GOOD ALBUM"


def test_search_order_falls_back_to_defaults_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config, "_release_json_search_paths",
        lambda: [str(tmp_path / "a.json"), str(tmp_path / "b.json")])

    data = config.load_release_config()
    assert data == DEFAULT_RELEASE


def test_search_paths_include_the_users_config_folder():
    # Confirms the fix from v1.6.0: release.json isn't ONLY read from
    # inside the packaged app anymore (which, once frozen, is a temp
    # folder nobody can actually edit) — it also checks the same folder
    # settings are saved in, which anyone can reach.
    paths = config._release_json_search_paths()
    assert os.path.join(config._cfg_dir, "release.json") in paths
