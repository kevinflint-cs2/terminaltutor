from datetime import datetime, timezone, timedelta
import importlib

import terminaltutor as cli

def test_interval_map():
    assert cli.interval_for_box(1) == timedelta(days=0)
    assert cli.interval_for_box(2) == timedelta(days=1)
    assert cli.interval_for_box(3) == timedelta(days=3)
    assert cli.interval_for_box(4) == timedelta(days=7)
    assert cli.interval_for_box(5) == timedelta(days=21)

def test_schedule_after_monkeypatch(monkeypatch):
    fixed = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)
    # full interval (Box 2 = +1 day)
    due = cli.schedule_after(2, factor=1.0)
    assert due == fixed + timedelta(days=1)
    # half interval (Box 2 = +12h)
    due_half = cli.schedule_after(2, factor=0.5)
    assert due_half == fixed + timedelta(hours=12)
