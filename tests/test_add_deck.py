from pathlib import Path
from datetime import datetime, timezone
import argparse

import terminaltutor as cli

def test_add_merges_unique_ids(tmp_path, monkeypatch):
    fixed = datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(cli, "utcnow", lambda: fixed)

    deck1 = tmp_path / "d1.csv"
    deck1.write_text("q,a,id\nQ1,A1,one\nQ2,A2,two\n", encoding="utf-8")
    state_file = tmp_path / "state.json"

    cli.cmd_init(argparse.Namespace(deck=str(deck1), state=str(state_file), force=False))
    state = cli.require_state(state_file)
    assert set(state.cards.keys()) == {"one", "two"}

    deck2 = tmp_path / "d2.json"
    deck2.write_text('[{"q":"Q3","a":"A3","id":"three"},{"q":"Q1","a":"A1","id":"one"}]', encoding="utf-8")

    cli.cmd_add(argparse.Namespace(deck=str(deck2), state=str(state_file)))

    state = cli.require_state(state_file)
    assert set(state.cards.keys()) == {"one", "two", "three"}
