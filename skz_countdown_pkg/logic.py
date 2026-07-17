"""
The "math brain" of the countdown, with no window, no buttons, nothing you
can click — just numbers in, numbers out. Because these functions don't
touch the screen, we can test them directly with pytest (see tests/) instead
of only being able to check them by staring at the running app.
"""

from zoneinfo import ZoneInfo

from .config import MILESTONES


def split_remaining(total_seconds):
    """Turn a number of leftover seconds into (weeks, days, hours, minutes,
    seconds) — the same split the 5 big number boxes show on screen.

    total_seconds should already be a whole number of seconds, 0 or more.
    """
    weeks, rem = divmod(total_seconds, 7 * 24 * 3600)
    days, rem = divmod(rem, 24 * 3600)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    return weeks, days, hours, minutes, seconds


def milestones_crossed(remaining, fired, settings, milestones=MILESTONES):
    """Which big moments have we just passed that we haven't announced yet?

    remaining  : how many seconds are left until release (can be negative,
                 if the release has already happened)
    fired      : a set of milestone keys we've ALREADY sent an alert for
    settings   : the saved settings dict — a milestone only counts if its
                 switch is turned on
    milestones : the list of (key, label, seconds_before) big moments,
                 defaulting to the app's real MILESTONES list

    Returns a list of (key, label, seconds_before) tuples, in the same
    order as `milestones`, for every moment that's newly crossed.
    """
    return [
        (key, label, secs)
        for key, label, secs in milestones
        if key not in fired
        and settings.get(key, True)
        and remaining <= secs
    ]


def local_display_dt(dt, zone_name=None):
    """Where a moment in time lands on a particular clock — worked out
    CORRECTLY for that exact moment, not "whatever the rule happens to be
    today." A place can use different clock-offsets at different times of
    year (daylight saving), so converting a WINTER release and a SUMMER
    release both need to ask "what was the rule on THAT day", not reuse
    today's answer for both.

    zone_name=None means "whatever timezone this computer is set to" — the
    normal, real case. Passing an explicit zone_name (like
    "America/New_York") is mainly so tests can check the daylight-saving
    math is right without depending on which timezone the test happens to
    be running in.
    """
    if zone_name is None:
        return dt.astimezone()
    return dt.astimezone(ZoneInfo(zone_name))
