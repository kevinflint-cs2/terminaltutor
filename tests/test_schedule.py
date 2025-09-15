from datetime import UTC, datetime, timedelta

import terminaltutor as cli  # updated module name


def test_interval_map():
    assert cli.interval_for_box(1) == timedelta(days=0)
    assert cli.interval_for_box(2) == timedelta(days=1)
    assert cli.interval_for_box(3) == timedelta(days=3)
    assert cli.interval_for_box(4) == timedelta(days=7)
    assert cli.interval_for_box(5) == timedelta(days=21)


def test_schedule_after_full_interval(monkeypatch):
    fixed = datetime(2025, 1, 1, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)
    # schedule_after uses the full interval for the given box
    due = cli.schedule_after(2)  # Box 2 = +1 day
    assert due == fixed + timedelta(days=1)


def test_promote_and_demote_bounds():
    # +1 step
    assert cli.promote(1, n=1) == 2
    # +2 steps (used by high confidence)
    assert cli.promote(3, n=2) == 5
    # cap at MAX_BOX
    assert cli.promote(5, n=2) == 5
    # demote always to 1
    assert cli.demote_to_1() == 1
