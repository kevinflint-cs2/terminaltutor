# TerminalTutor

**TerminalTutor** is a tiny, dependency-free Python CLI for mastering exams from your terminal. It implements a **Leitner spaced-repetition system** with **confidence tagging**, so you review missed items more often and space out what you know.

## Features

* **Leitner boxes (1–5):** Default intervals of 0, 1, 3, 7, and 21 days (fully configurable).
* **Confidence tagging:**
  `l` (low) → reset to Box 1, due now
  `m` (medium) → promote, half interval
  `h` (high) → promote, full interval
* **Fast CLI workflow:** `init`, `study`, `due`, `stats`, `add`.
* **Simple decks:** CSV (`q,a`) or JSON (`[{ "q": "...", "a": "..." }]`).
* **Progress persistence:** Lightweight JSON state with per-card box, next due time, and history.
* **Zero dependencies:** Runs anywhere Python 3 is available.

## Quick Start

```bash
# 1) Create a deck (CSV with headers q,a)
echo "q,a
What is CIA triad?,Confidentiality Integrity Availability
Azure secret store?,Azure Key Vault" > deck.csv

# 2) Initialize state
python leitner_cli.py init deck.csv

# 3) Study (due items, shuffled, up to 20 cards)
python leitner_cli.py study --shuffle --limit 20

# 4) Check progress and upcoming reviews
python leitner_cli.py stats
python leitner_cli.py due --limit 30
```

During study:

* Press **Enter** to reveal the answer.
* Grade with **l/m/h** to schedule the next review automatically.

## Why TerminalTutor?

* **Learn faster:** More exposure to weak items, less time on mastered ones.
* **Stay consistent:** Built-in scheduling enforces spacing across days.
* **Minimal friction:** One file, human-readable decks, version-friendly state.

## Customize

Adjust intervals in `BOX_INTERVALS_DAYS`, or change the promotion logic for `m`/`h` to match your tolerance. Import new material anytime with `add`.

Perfect for certification prep, language vocab, command flags, acronyms—anything Q/A shaped.