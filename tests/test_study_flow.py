from datetime import datetime, timezone, timedelta
from pathlib import Path
import argparse

import terminaltutor as cli

def write_deck_csv(tmp_path: Path) -> Path:
    p = tmp_path / "deck.csv"
    p.write_text("q,a\nQ1,A1\n", encoding="utf-8")
    return p

def test_study_promote_high_confidence(tmp_path, monkeypatch, capsys):
    deck = write_deck_csv(tmp_path)
    state_file = tmp_path / "state.json"

    fixed = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    # init
    cli.cmd_init(argparse.Namespace(deck=str(deck), state=str(state_file), force=False))

    # Simulate Enter (reveal) then 'h' (high confidence)
    inputs = iter(["", "h"])
    monkeypatch.setattr(cli, "ask", lambda prompt: next(inputs, "q"))

    # Run study for 1 card
    cli.cmd_study(argparse.Namespace(state=str(state_file), limit=1, all=False, shuffle=False))

    # Verify promotion from box 1 -> 2 and full interval applied (+1 day)
    state = cli.require_state(state_file)
    cid = next(iter(state.progress))
    st = state.progress[cid]
    assert st.box == 2
    assert cli.from_iso(st.next_due) == fixed + timedelta(days=1)

def test_study_demote_low_confidence(tmp_path, monkeypatch):
    deck = tmp_path / "deck.csv"
    deck.write_text("q,a\nQ1,A1\nQ2,A2\n", encoding="utf-8")
    state_file = tmp_path / "state.json"

    fixed = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    cli.cmd_init(argparse.Namespace(deck=str(deck), state=str(state_file), force=False))
    state = cli.require_state(state_file)

    # Put first card in box 2 to test demotion
    first_id = next(iter(state.progress))
    st = state.progress[first_id]
    st.box = 2
    st.next_due = cli.to_iso(fixed)  # due now
    cli.save_state(state, state_file)

    # Simulate Enter then 'l' (low -> wrong)
    inputs = iter(["", "l"])
    monkeypatch.setattr(cli, "ask", lambda prompt: next(inputs, "q"))

    cli.cmd_study(argparse.Namespace(state=str(state_file), limit=1, all=False, shuffle=False))

    state = cli.require_state(state_file)
    st = state.progress[first_id]
    assert st.box == 1
    # due "now" for wrong answers
    assert cli.from_iso(st.next_due) == fixed
