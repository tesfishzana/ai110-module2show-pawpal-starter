# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Smarter Scheduling

Beyond the basic greedy planner, PawPal+ includes four algorithmic features:

**Sorting** — `Scheduler.sort_by_duration()` orders tasks shortest-first (or longest-first) so you can see at a glance which tasks are quick wins. `sort_by_due_date()` surfaces the most urgent tasks regardless of priority level.

**Filtering** — `Scheduler.filter_tasks()` narrows any task list by pet name, completion status, or category. Useful for answering questions like "what does Mochi still have left today?" or "which feeding tasks are across all pets?"

**Recurring task renewal** — `Scheduler.mark_task_complete(task, pet)` marks a task done and automatically queues the next occurrence. Daily tasks reappear tomorrow; weekly tasks reappear in seven days. As-needed tasks (like a vet visit) are not renewed automatically.

**Conflict detection** — `Scheduler.detect_conflicts(schedule)` scans a list of scheduled entries for overlapping time slots using the standard interval test. It returns plain-English warnings rather than raising exceptions, so the app can surface the issue to the user without crashing.

## Testing PawPal+

Run the full test suite from the project root:

```bash
python -m pytest
# or for verbose output:
python -m pytest -v
```

The suite lives in `tests/test_pawpal.py` and contains **49 tests** across five areas:

| Area | What's covered |
|---|---|
| Task lifecycle | Creation defaults, `mark_complete()`, idempotency, isolation between tasks |
| Recurrence | Daily (+1 day), weekly (+7 days), as-needed (no renewal), `due_date=None` fallback, attribute preservation |
| Pet management | Add, remove, `pending_tasks()`, removing a task that was never added, all-done edge case |
| Sorting | Duration ascending/descending, single-item and empty lists, due-date ordering, `None` dates sort last |
| Scheduler | No pets, no tasks, zero time budget, task exactly fills budget, one minute over budget, priority ordering, all-completed input, combined filtering, conflict detection (clean, single overlap, same-start-time, three-way overlap, empty/single-entry) |

Each test is labelled with a short comment explaining what could go wrong without that specific check — the goal is that any future change to `pawpal_system.py` that breaks behaviour will be caught immediately.

**Confidence: ★★★★☆**

The core scheduling, sorting, filtering, and recurrence paths are thoroughly covered including boundary conditions. The main gap is integration-level tests for the Streamlit UI itself (button clicks, session-state persistence) and end-to-end tests that simulate a full user session from pet creation to schedule output.
