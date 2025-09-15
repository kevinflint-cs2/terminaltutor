import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import terminaltutor as cli  # updated module name


def write_deck_csv(tmp_path: Path) -> Path:
    p = tmp_path / "deck.csv"
    p.write_text(
        "q,a\n"
        "What is CIA triad?,Confidentiality Integrity Availability\n"
        "Azure secret store?,Azure Key Vault\n",
        encoding="utf-8",
    )
    return p


def test_init_creates_state(tmp_path, monkeypatch):
    deck = write_deck_csv(tmp_path)

    fixed = datetime(2025, 1, 1, 8, 0, tzinfo=UTC)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    # initialize into <tmp_path>/state.json via state_dir
    cli.cmd_init(argparse.Namespace(deck=str(deck), state_dir=str(tmp_path), force=False))

    state_path = cli.resolve_state_path(str(tmp_path))
    assert state_path.exists()

    state = cli.require_state(state_path)
    assert len(state.cards) == 2
    # All start in box 1 and are due now
    for st in state.progress.values():
        assert st.box == 1
        assert cli.from_iso(st.next_due) == fixed


def test_due_cards_filtering(tmp_path, monkeypatch):
    deck = write_deck_csv(tmp_path)

    fixed = datetime(2025, 1, 1, 8, 0, tzinfo=UTC)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    cli.cmd_init(argparse.Namespace(deck=str(deck), state_dir=str(tmp_path), force=False))

    state_path = cli.resolve_state_path(str(tmp_path))
    state = cli.require_state(state_path)

    # Make one card due in the future
    ids = list(state.progress.keys())
    state.progress[ids[0]].next_due = cli.to_iso(fixed + timedelta(hours=2))
    cli.save_state(state, state_path)

    only_due = cli.due_cards(state, include_not_due=False)
    assert len(only_due) == 1  # one due now

    all_cards = cli.due_cards(state, include_not_due=True)
    assert len(all_cards) == 2
