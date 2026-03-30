"""
main.py — CLI demo that exercises every algorithmic feature in pawpal_system.py.

Run with:  python main.py
"""

from datetime import date

from pawpal_system import Owner, Pet, Priority, ScheduledTask, Scheduler, Task


def section(title: str) -> None:
    print(f"\n{'=' * 55}")
    print(f"  {title}")
    print("=" * 55)


def main():
    # -----------------------------------------------------------------
    # Basic setup — owner with two pets
    # -----------------------------------------------------------------
    jordan = Owner(name="Jordan", available_minutes=120)

    mochi = Pet(name="Mochi", species="dog", age_years=3)
    luna = Pet(name="Luna", species="cat", age_years=5)

    # Tasks added intentionally out of duration order to show sorting later
    mochi.add_task(Task("Fetch in the yard",   "enrichment", duration_minutes=20, frequency="daily",  priority=Priority.LOW,    due_date=date.today()))
    mochi.add_task(Task("Morning walk",         "walk",       duration_minutes=30, frequency="daily",  priority=Priority.HIGH,   due_date=date.today()))
    mochi.add_task(Task("Breakfast feeding",    "feeding",    duration_minutes=10, frequency="daily",  priority=Priority.HIGH,   due_date=date.today()))
    mochi.add_task(Task("Flea medication",      "medication", duration_minutes=5,  frequency="weekly", priority=Priority.MEDIUM, due_date=date.today()))

    luna.add_task(Task("Brush coat",            "grooming",   duration_minutes=15, frequency="weekly", priority=Priority.LOW,    due_date=date.today()))
    luna.add_task(Task("Feed wet food",         "feeding",    duration_minutes=5,  frequency="daily",  priority=Priority.HIGH,   due_date=date.today()))
    luna.add_task(Task("Clean litter box",      "grooming",   duration_minutes=10, frequency="daily",  priority=Priority.MEDIUM, due_date=date.today()))

    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    scheduler = Scheduler(owner=jordan)
    all_tasks = scheduler.get_all_tasks()

    # -----------------------------------------------------------------
    # Step 2a — Sorting by duration
    # -----------------------------------------------------------------
    section("SORT BY DURATION (shortest first)")
    by_duration = scheduler.sort_by_duration(all_tasks, ascending=True)
    for t in by_duration:
        print(f"  {t.duration_minutes:>3} min  |  {t.description}")

    section("SORT BY DUE DATE")
    by_date = scheduler.sort_by_due_date(all_tasks)
    for t in by_date:
        print(f"  {t.due_date}  |  {t.description}")

    # -----------------------------------------------------------------
    # Step 2b — Filtering
    # -----------------------------------------------------------------
    section("FILTER — Mochi's tasks only")
    mochi_tasks = scheduler.filter_tasks(all_tasks, pet_name="Mochi")
    for t in mochi_tasks:
        print(f"  {t}")

    section("FILTER — pending tasks only (not yet completed)")
    pending = scheduler.filter_tasks(all_tasks, completed=False)
    print(f"  {len(pending)} task(s) still to do today")

    section("FILTER — feeding tasks across all pets")
    feeding = scheduler.filter_tasks(all_tasks, category="feeding")
    for t in feeding:
        print(f"  {t.description}")

    # -----------------------------------------------------------------
    # Step 3 — Recurring task renewal
    # -----------------------------------------------------------------
    section("RECURRING TASK RENEWAL")

    walk = mochi.tasks[1]  # "Morning walk" — daily
    print(f"  Marking complete: {walk.description}")
    renewal = scheduler.mark_task_complete(walk, mochi)

    if renewal:
        print(f"  Auto-renewed:     {renewal.description}  (due {renewal.due_date})")
    else:
        print("  No renewal (as-needed task)")

    flea_med = mochi.tasks[3]  # "Flea medication" — weekly
    print(f"\n  Marking complete: {flea_med.description}")
    renewal2 = scheduler.mark_task_complete(flea_med, mochi)
    if renewal2:
        print(f"  Auto-renewed:     {renewal2.description}  (due {renewal2.due_date})")

    # Verify completed tasks don't sneak into the schedule
    pending_after = scheduler.filter_tasks(mochi.tasks, completed=False)
    print(f"\n  Mochi's pending tasks after completing two: {len(pending_after)}")

    # -----------------------------------------------------------------
    # Step 4 — Conflict detection
    # -----------------------------------------------------------------
    section("CONFLICT DETECTION — normal schedule (expect no conflicts)")

    # Rebuild scheduler so it picks up the renewed tasks
    scheduler = Scheduler(owner=jordan)
    schedule = scheduler.generate_schedule()
    conflicts = scheduler.detect_conflicts(schedule)
    if conflicts:
        for w in conflicts:
            print(w)
    else:
        print("  No conflicts detected — all slots are clean.")

    section("CONFLICT DETECTION — manufactured overlapping schedule")

    # Manually create two ScheduledTasks that overlap to show the detector works.
    # Task A: starts at 0 min, lasts 30 min (ends at 30)
    # Task B: starts at 20 min, lasts 20 min (ends at 40) — overlaps A by 10 min
    task_a = Task("Task A", "walk",    duration_minutes=30, frequency="daily")
    task_b = Task("Task B", "feeding", duration_minutes=20, frequency="daily")
    fake_schedule = [
        ScheduledTask(task=task_a, pet_name="Mochi", start_minute=0,  reason="demo"),
        ScheduledTask(task=task_b, pet_name="Luna",  start_minute=20, reason="demo"),
    ]
    conflicts = scheduler.detect_conflicts(fake_schedule)
    for w in conflicts:
        print(w)

    # -----------------------------------------------------------------
    # Final schedule
    # -----------------------------------------------------------------
    section("TODAY'S SCHEDULE")
    for entry in schedule:
        done_marker = "[done]" if entry.task.is_completed else "      "
        print(f"  {done_marker} {entry.time_label()}  |  {entry.pet_name:<6}  |  {entry.task.description}")
    print("=" * 55)
    print("\n" + scheduler.explain_plan(schedule))


if __name__ == "__main__":
    main()
