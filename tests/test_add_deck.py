import argparse
from datetime import UTC, datetime

import terminaltutor as cli  # ← use the new module name


def test_add_merges_unique_ids(tmp_path, monkeypatch):
    fixed = datetime(2025, 1, 1, 11, 0, tzinfo=UTC)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    # First deck
    deck1 = tmp_path / "d1.csv"
    deck1.write_text("q,a,id\nQ1,A1,one\nQ2,A2,two\n", encoding="utf-8")

    # Initialize state in <tmp_path>/state.json
    cli.cmd_init(argparse.Namespace(deck=str(deck1), state_dir=str(tmp_path), force=False))

    # Resolve the actual state.json path for direct reads
    state_path = cli.resolve_state_path(str(tmp_path))
    state = cli.require_state(state_path)
    assert set(state.cards.keys()) == {"one", "two"}

    # Second deck (one new, one duplicate id)
    deck2 = tmp_path / "d2.json"
    deck2.write_text(
        '[{"q":"Q3","a":"A3","id":"three"},{"q":"Q1","a":"A1","id":"one"}]', encoding="utf-8"
    )

    # Add using state_dir (not state file)
    cli.cmd_add(argparse.Namespace(deck=str(deck2), state_dir=str(tmp_path)))

    state = cli.require_state(state_path)
    assert set(state.cards.keys()) == {"one", "two", "three"}
