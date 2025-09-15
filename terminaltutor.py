#!/usr/bin/env python3
# Tiny Leitner CLI with confidence tagging.
# - Boxes: 1..5 with intervals {1:0d, 2:1d, 3:3d, 4:7d, 5:21d}
# - Deck from CSV (q,a) or JSON ([{"q": "...", "a": "..."}])
# - State persisted in JSON (card box, next_due, history)

import argparse
import csv
import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

STATE_FILE_DEFAULT = Path("leitner_state.json")
MAX_BOX = 5
BOX_INTERVALS_DAYS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 21}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def from_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


@dataclass
class Card:
    id: str
    q: str
    a: str


@dataclass
class CardState:
    box: int
    next_due: str  # ISO datetime
    last_conf: Optional[str] = None  # "l"|"m"|"h"|None
    reps: int = 0  # total reviews


@dataclass
class State:
    created: str
    cards: Dict[str, Card]
    progress: Dict[str, CardState]  # keyed by card.id
    history: List[dict]


# ---------- I/O ----------

def load_state(path: Path) -> Optional[State]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    cards = {k: Card(**v) for k, v in raw["cards"].items()}
    progress = {k: CardState(**v) for k, v in raw["progress"].items()}
    return State(
        created=raw["created"],
        cards=cards,
        progress=progress,
        history=raw.get("history", []),
    )


def save_state(state: State, path: Path) -> None:
    serial = {
        "created": state.created,
        "cards": {k: asdict(v) for k, v in state.cards.items()},
        "progress": {k: asdict(v) for k, v in state.progress.items()},
        "history": state.history,
    }
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(serial, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


# ---------- Deck loading ----------

def load_deck(deck_path: Path) -> List[Card]:
    if deck_path.suffix.lower() == ".csv":
        return load_deck_csv(deck_path)
    elif deck_path.suffix.lower() == ".json":
        return load_deck_json(deck_path)
    else:
        raise SystemExit("Deck must be .csv or .json")


def load_deck_csv(path: Path) -> List[Card]:
    cards: List[Card] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        # Expect columns: q, a  (id optional)
        line_no = 0
        for row in reader:
            line_no += 1
            q = (row.get("q") or "").strip()
            a = (row.get("a") or "").strip()
            if not q or not a:
                continue
            cid = (row.get("id") or f"csv:{line_no}").strip()
            cards.append(Card(id=cid, q=q, a=a))
    if not cards:
        raise SystemExit("No cards found in CSV. Need columns: q,a (id optional).")
    return cards


def load_deck_json(path: Path) -> List[Card]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    cards: List[Card] = []
    for i, item in enumerate(data, start=1):
        q = (item.get("q") or "").strip()
        a = (item.get("a") or "").strip()
        if not q or not a:
            continue
        cid = (item.get("id") or f"json:{i}").strip()
        cards.append(Card(id=cid, q=q, a=a))
    if not cards:
        raise SystemExit("No cards found in JSON. Expect list of {q,a,id?}.")
    return cards


# ---------- Scheduling ----------

def interval_for_box(box: int) -> timedelta:
    days = BOX_INTERVALS_DAYS.get(box, BOX_INTERVALS_DAYS[MAX_BOX])
    return timedelta(days=days)


def schedule_after(box: int, factor: float = 1.0) -> datetime:
    base = interval_for_box(box)
    delta = timedelta(seconds=max(0, int(base.total_seconds() * factor)))
    return utcnow() + delta


def promote(box: int) -> int:
    return min(MAX_BOX, box + 1)


def demote_to_1() -> int:
    return 1


# ---------- Commands ----------

def cmd_init(args: argparse.Namespace) -> None:
    deck = load_deck(Path(args.deck))
    if args.state and Path(args.state).exists() and not args.force:
        raise SystemExit(
            f"State file {args.state} exists. Use --force to overwrite."
        )
    now = to_iso(utcnow())
    cards = {c.id: c for c in deck}
    progress = {
        c.id: CardState(box=1, next_due=now) for c in deck
    }
    state = State(created=now, cards=cards, progress=progress, history=[])
    save_state(state, Path(args.state))
    print(f"Initialized {len(deck)} cards into {args.state}")


def due_cards(state: State, include_not_due: bool = False) -> List[str]:
    now = utcnow()
    items = []
    for cid, st in state.progress.items():
        due = from_iso(st.next_due)
        if include_not_due or due <= now:
            items.append((cid, due))
    # sort by next_due, then randomize slightly within same due window
    items.sort(key=lambda t: t[1])
    # Keep as list of ids
    return [cid for cid, _ in items]


def cmd_due(args: argparse.Namespace) -> None:
    state = require_state(Path(args.state))
    ids = due_cards(state, include_not_due=args.all)
    print(f"Due count: {len([i for i in ids if from_iso(state.progress[i].next_due) <= utcnow()])}")
    print(f"Total fetched (respecting --all): {len(ids)}")
    for cid in ids[: args.limit or 50]:
        st = state.progress[cid]
        print(
            f"- {cid} | box {st.box} | due {from_iso(st.next_due).astimezone().strftime('%Y-%m-%d %H:%M')}"
        )


def require_state(path: Path) -> State:
    state = load_state(path)
    if state is None:
        raise SystemExit(f"No state found at {path}. Run 'init' first.")
    return state


def cmd_stats(args: argparse.Namespace) -> None:
    state = require_state(Path(args.state))
    box_counts = {b: 0 for b in range(1, MAX_BOX + 1)}
    due_count = 0
    now = utcnow()
    for st in state.progress.values():
        box_counts[st.box] += 1
        if from_iso(st.next_due) <= now:
            due_count += 1
    total = len(state.progress)
    print(f"Total cards: {total}")
    print(f"Due now: {due_count}")
    for b in range(1, MAX_BOX + 1):
        print(f"  Box {b}: {box_counts[b]}")
    if state.history:
        last = state.history[-1]
        print(f"Last review: {last.get('ts')} — card {last.get('cid')} ({last.get('conf')})")


def ask(prompt: str) -> str:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"


def cmd_study(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = require_state(path)
    pool = due_cards(state, include_not_due=args.all)
    if not pool:
        print("Nothing due. Use --all to include not-due cards, or come back later.")
        return

    if args.shuffle:
        random.shuffle(pool)

    limit = args.limit or len(pool)
    taken = 0

    print("Study mode: [Enter]=show answer | then grade: (l)ow wrong, (m)edium, (h)igh | (s)kip | (q)uit")
    for cid in pool:
        if taken >= limit:
            break
        card = state.cards[cid]
        st = state.progress[cid]

        print("\n" + "-" * 70)
        print(f"[{taken+1}/{limit}] Box {st.box}  Due: {from_iso(st.next_due).astimezone().strftime('%Y-%m-%d %H:%M')}")
        print(f"Q: {card.q}")
        key = ask("Press Enter to reveal, or (s)kip/(q)uit: ").strip().lower()
        if key == "q":
            break
        if key == "s":
            continue

        print(f"A: {card.a}")
        conf = ask("Grade (l/m/h), or (q)uit: ").strip().lower()
        if conf == "q":
            break
        if conf not in {"l", "m", "h"}:
            print("Invalid; treating as 'l'.")
            conf = "l"

        old_box = st.box
        if conf == "l":
            st.box = demote_to_1()
            st.next_due = to_iso(schedule_after(st.box, factor=0.0))  # due now
        elif conf == "m":
            st.box = promote(st.box)
            st.next_due = to_iso(schedule_after(st.box, factor=0.5))  # half interval
        else:  # "h"
            st.box = promote(st.box)
            st.next_due = to_iso(schedule_after(st.box, factor=1.0))  # full interval

        st.last_conf = conf
        st.reps += 1

        state.history.append(
            {
                "ts": to_iso(utcnow()),
                "cid": cid,
                "old_box": old_box,
                "new_box": st.box,
                "conf": conf,
            }
        )
        save_state(state, path)
        taken += 1

    print("\nSession complete.")
    cmd_stats(argparse.Namespace(state=str(path)))


def cmd_add(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = require_state(path)
    # Add from CSV/JSON deck file
    new_cards = load_deck(Path(args.deck))
    existing_ids = set(state.cards.keys())
    added = 0
    nowiso = to_iso(utcnow())
    for c in new_cards:
        if c.id in existing_ids:
            continue
        state.cards[c.id] = c
        state.progress[c.id] = CardState(box=1, next_due=nowiso)
        added += 1
    save_state(state, path)
    print(f"Added {added} new cards.")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tiny Leitner CLI with confidence tagging.")
    p.add_argument("--state", default=str(STATE_FILE_DEFAULT), help="Path to state JSON file (default: leitner_state.json)")

    sub = p.add_subparsers(dest="cmd", required=True)

    sp_init = sub.add_parser("init", help="Initialize state from a deck file")
    sp_init.add_argument("deck", help="Path to deck (.csv with columns q,a or .json)")
    sp_init.add_argument("--force", action="store_true", help="Overwrite existing state file")
    sp_init.set_defaults(func=cmd_init)

    sp_study = sub.add_parser("study", help="Run a study session")
    sp_study.add_argument("--limit", type=int, help="Max cards this session")
    sp_study.add_argument("--all", action="store_true", help="Include not-due cards to fill session")
    sp_study.add_argument("--shuffle", action="store_true", help="Shuffle due pool before starting")
    sp_study.set_defaults(func=cmd_study)

    sp_stats = sub.add_parser("stats", help="Show counts per box and due")
    sp_stats.set_defaults(func=cmd_stats)

    sp_due = sub.add_parser("due", help="List due cards")
    sp_due.add_argument("--limit", type=int, help="Limit listing")
    sp_due.add_argument("--all", action="store_true", help="Include not-due")
    sp_due.set_defaults(func=cmd_due)

    sp_add = sub.add_parser("add", help="Append cards from another deck file")
    sp_add.add_argument("deck", help="Path to deck (.csv or .json)")
    sp_add.set_defaults(func=cmd_add)

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()