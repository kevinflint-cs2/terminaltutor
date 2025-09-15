import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import terminaltutor as cli  # updated module name


def write_deck_csv(tmp_path: Path) -> Path:
    p = tmp_path / "deck.csv"
    p.write_text("q,a\nQ1,A1\n", encoding="utf-8")
    return p


def test_study_promote_high_confidence_plus2(tmp_path, monkeypatch):
    deck = write_deck_csv(tmp_path)
    state_dir = str(tmp_path)

    fixed = datetime(2025, 1, 1, 9, 0, tzinfo=UTC)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    # init
    cli.cmd_init(argparse.Namespace(deck=str(deck), state_dir=state_dir, force=False))

    # Simulate Enter (reveal) then 'h' (high → +2 boxes, full interval)
    inputs = iter(["", "h"])
    monkeypatch.setattr(cli, "ask", lambda prompt: next(inputs, "q"))

    cli.cmd_study(argparse.Namespace(state_dir=state_dir, limit=1, all=False, shuffle=False))

    state = cli.require_state(cli.resolve_state_path(state_dir))
    cid = next(iter(state.progress))
    st = state.progress[cid]
    assert st.box == 3  # 1 -> 3
    assert cli.from_iso(st.next_due) == fixed + timedelta(days=3)  # Box 3 interval


def test_study_promote_medium_plus1(tmp_path, monkeypatch):
    deck = write_deck_csv(tmp_path)
    state_dir = str(tmp_path)

    fixed = datetime(2025, 1, 2, 10, 0, tzinfo=UTC)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    cli.cmd_init(argparse.Namespace(deck=str(deck), state_dir=state_dir, force=False))

    # Simulate Enter then 'm' (medium → +1 box, full interval)
    inputs = iter(["", "m"])
    monkeypatch.setattr(cli, "ask", lambda prompt: next(inputs, "q"))

    cli.cmd_study(argparse.Namespace(state_dir=state_dir, limit=1, all=False, shuffle=False))

    state = cli.require_state(cli.resolve_state_path(state_dir))
    cid = next(iter(state.progress))
    st = state.progress[cid]
    assert st.box == 2  # 1 -> 2
    assert cli.from_iso(st.next_due) == fixed + timedelta(days=1)  # Box 2 interval


def test_study_demote_low_confidence(tmp_path, monkeypatch):
    deck = tmp_path / "deck.csv"
    deck.write_text("q,a\nQ1,A1\nQ2,A2\n", encoding="utf-8")
    state_dir = str(tmp_path)

    fixed = datetime(2025, 1, 3, 11, 0, tzinfo=UTC)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    cli.cmd_init(argparse.Namespace(deck=str(deck), state_dir=state_dir, force=False))
    state_path = cli.resolve_state_path(state_dir)
    state = cli.require_state(state_path)

    # Put first card in box 2 and due now
    first_id = next(iter(state.progress))
    st = state.progress[first_id]
    st.box = 2
    st.next_due = cli.to_iso(fixed)
    cli.save_state(state, state_path)

    # Simulate Enter then 'l' (low → reset to box 1, due now)
    inputs = iter(["", "l"])
    monkeypatch.setattr(cli, "ask", lambda prompt: next(inputs, "q"))

    cli.cmd_study(argparse.Namespace(state_dir=state_dir, limit=1, all=False, shuffle=False))

    state = cli.require_state(state_path)
    st = state.progress[first_id]
    assert st.box == 1
    assert cli.from_iso(st.next_due) == fixed
