# PawPal+

A Streamlit app that helps a pet owner plan daily care tasks across multiple pets. You enter your pets, describe what each one needs, and PawPal+ builds a prioritised schedule that fits within the time you have — and explains every decision it makes.

---

## 📸 Demo

<a href="/course_images/ai110/pawpal_screenshot.png" target="_blank">
  <img src='/course_images/ai110/pawpal_screenshot.png' title='PawPal App' width='' alt='PawPal App' class='center-block' />
</a>

---

## Features

**Owner and pet management**
- Register an owner with a daily time budget (in minutes)
- Add multiple pets (name, species, age)
- Tasks are attached to individual pets and stored in session state so nothing resets on page refresh

**Task management**
- Add tasks with a description, category, duration, priority (high / medium / low), and frequency (daily / weekly / as-needed)
- Quick stats bar shows total / pending / completed counts at a glance
- Sort tasks by duration (shortest or longest first) or by due date
- Filter tasks by category or across all pets

**Smart scheduling**
- Greedy priority-first scheduler fits as many tasks as possible within the owner's time budget
- High-priority tasks are always evaluated before medium and low ones
- Completed tasks are excluded automatically
- Every scheduled entry includes a plain-English reason explaining why it was chosen
- Tasks that didn't fit are listed separately so nothing gets silently lost

**Recurring task renewal**
- Marking a daily task complete automatically queues the next occurrence for tomorrow
- Weekly tasks reappear seven days later
- As-needed tasks (e.g., vet visits) are not renewed — they're one-offs

**Conflict detection**
- After generating the schedule, `detect_conflicts()` scans for overlapping time slots
- Conflicts are shown as prominent warnings above the schedule table, not buried in logs
- The normal scheduler never produces conflicts, but the detector is there as a safety net for manual or future parallel scheduling

**Explain the plan**
- Expandable "Full plan explanation" section shows every scheduling decision in plain English
- Skipped tasks (not enough time) are listed with their duration and priority

---

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

---

## Project structure

```
pawpal_system.py   — backend logic (Owner, Pet, Task, Scheduler, ScheduledTask)
app.py             — Streamlit UI
main.py            — CLI demo script (run with: python main.py)
tests/
  test_pawpal.py   — 49 automated tests
reflection.md      — design journal and AI collaboration notes
```

---

## Testing PawPal+

```bash
python -m pytest        # run all tests
python -m pytest -v     # verbose output with test names
```

The suite in `tests/test_pawpal.py` covers **49 tests** across five areas:

| Area | What's covered |
|---|---|
| Task lifecycle | Creation defaults, `mark_complete()`, idempotency, isolation between tasks |
| Recurrence | Daily (+1 day), weekly (+7 days), as-needed (no renewal), `due_date=None` fallback, attribute preservation |
| Pet management | Add, remove, `pending_tasks()`, removing a task never added, all-done edge case |
| Sorting | Duration ascending/descending, single-item and empty lists, due-date ordering, `None` dates sort last |
| Scheduler | No pets, no tasks, zero time budget, exact-fill and one-minute-over boundary, priority ordering, all-completed input, combined filtering, conflict detection (clean, single overlap, same-start-time, three-way, empty/single-entry) |

Each test has an inline comment explaining what specific bug it protects against.

**Confidence: ★★★★☆** — Core logic is thoroughly covered. Main gap is UI-level and end-to-end tests.

---

## Architecture

Four classes plus one output type, all in `pawpal_system.py`:

- **`Task`** (dataclass) — a single care activity with description, category, duration, frequency, priority, and due date
- **`Pet`** (dataclass) — holds a list of Tasks; knows which ones are still pending
- **`Owner`** (dataclass) — holds the daily time budget and all pets; collects tasks across the household
- **`Scheduler`** — the logic layer; sorts, filters, schedules, detects conflicts, handles renewals
- **`ScheduledTask`** (dataclass) — output type pairing a Task with a start time, pet name, and reason

See the full UML class diagram in `reflection.md`.
