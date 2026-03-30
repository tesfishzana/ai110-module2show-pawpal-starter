"""
Test suite for PawPal+ (pawpal_system.py).

Test plan — 5 core behaviours verified:
  1. Task lifecycle  — creation, completion, recurrence
  2. Pet management  — adding, removing, querying tasks
  3. Sorting         — duration and due-date ordering, edge cases
  4. Filtering       — by pet, status, category, and combined
  5. Scheduler       — budget, priority, conflict detection, edge cases

Each section has a mix of happy-path tests and edge cases.  Edge cases are
labelled with a short comment explaining what could go wrong without the check.
"""

from datetime import date, timedelta

from pawpal_system import Owner, Pet, Priority, ScheduledTask, Scheduler, Task


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_task(
    description="Test task",
    duration=15,
    priority=Priority.MEDIUM,
    frequency="daily",
    category="other",
    due_date=None,
):
    return Task(
        description=description,
        category=category,
        duration_minutes=duration,
        priority=priority,
        frequency=frequency,
        due_date=due_date,
    )


def make_owner_with_pet(*tasks, available_minutes=120):
    """Build an Owner → Pet → [tasks] chain in one call."""
    owner = Owner(name="Jordan", available_minutes=available_minutes)
    pet = Pet(name="Mochi", species="dog")
    for t in tasks:
        pet.add_task(t)
    owner.add_pet(pet)
    return owner, pet


# ===========================================================================
# 1. Task lifecycle
# ===========================================================================

def test_new_task_is_not_completed():
    # A freshly created task must start in a pending state.
    task = make_task()
    assert task.is_completed is False


def test_mark_complete_changes_status():
    task = make_task("Give flea medication")
    task.mark_complete()
    assert task.is_completed is True


def test_mark_complete_is_idempotent():
    # Calling mark_complete twice shouldn't raise or flip the flag back.
    task = make_task("Walk")
    task.mark_complete()
    task.mark_complete()
    assert task.is_completed is True


def test_mark_complete_does_not_affect_other_tasks():
    # Completing one task must leave unrelated tasks untouched.
    t1 = make_task("Walk")
    t2 = make_task("Feed")
    t1.mark_complete()
    assert t2.is_completed is False


# --- Recurrence ---

def test_next_occurrence_daily_adds_one_day():
    today = date.today()
    task = Task("Morning walk", "walk", 30, frequency="daily", due_date=today)
    renewal = task.next_occurrence()
    assert renewal is not None
    assert renewal.due_date == today + timedelta(days=1)
    assert renewal.is_completed is False


def test_next_occurrence_weekly_adds_seven_days():
    today = date.today()
    task = Task("Flea meds", "medication", 5, frequency="weekly", due_date=today)
    renewal = task.next_occurrence()
    assert renewal is not None
    assert renewal.due_date == today + timedelta(days=7)


def test_next_occurrence_preserves_task_attributes():
    # The renewal should be an identical copy except for due_date and is_completed.
    today = date.today()
    task = Task("Brush coat", "grooming", 15, frequency="weekly",
                priority=Priority.HIGH, due_date=today)
    renewal = task.next_occurrence()
    assert renewal.description == task.description
    assert renewal.category == task.category
    assert renewal.duration_minutes == task.duration_minutes
    assert renewal.priority == task.priority
    assert renewal.frequency == task.frequency


def test_next_occurrence_without_due_date_defaults_to_tomorrow():
    # When due_date is None the renewal should still produce a sensible date.
    task = Task("Morning walk", "walk", 30, frequency="daily")  # no due_date
    renewal = task.next_occurrence()
    assert renewal is not None
    assert renewal.due_date == date.today() + timedelta(days=1)


def test_next_occurrence_as_needed_returns_none():
    # As-needed tasks have no predictable cadence — no renewal should be created.
    task = Task("Vet visit", "medication", 60, frequency="as-needed")
    assert task.next_occurrence() is None


# ===========================================================================
# 2. Pet management
# ===========================================================================

def test_new_pet_has_no_tasks():
    pet = Pet(name="Mochi", species="dog")
    assert pet.tasks == []


def test_add_task_increases_task_count():
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(make_task("Walk"))
    assert len(pet.tasks) == 1
    pet.add_task(make_task("Feed"))
    assert len(pet.tasks) == 2


def test_remove_task_decreases_task_count():
    pet = Pet(name="Luna", species="cat")
    task = make_task("Brush coat")
    pet.add_task(task)
    pet.remove_task(task)
    assert len(pet.tasks) == 0


def test_remove_nonexistent_task_is_safe():
    # Removing a task that was never added should not crash or corrupt the list.
    pet = Pet(name="Luna", species="cat")
    orphan = make_task("Ghost task")
    pet.add_task(make_task("Real task"))
    pet.remove_task(orphan)
    assert len(pet.tasks) == 1


def test_pending_tasks_excludes_completed():
    pet = Pet(name="Mochi", species="dog")
    done = make_task("Old walk")
    done.mark_complete()
    pending = make_task("Evening walk")
    pet.add_task(done)
    pet.add_task(pending)
    assert len(pet.pending_tasks()) == 1
    assert pet.pending_tasks()[0].description == "Evening walk"


def test_pending_tasks_all_done_returns_empty():
    # Edge case: if every task is complete, pending list should be empty.
    pet = Pet(name="Mochi", species="dog")
    for desc in ("Walk", "Feed", "Med"):
        t = make_task(desc)
        t.mark_complete()
        pet.add_task(t)
    assert pet.pending_tasks() == []


# ===========================================================================
# 3. Sorting
# ===========================================================================

def test_sort_by_duration_ascending():
    owner, _ = make_owner_with_pet(
        make_task("Long",   duration=60),
        make_task("Short",  duration=10),
        make_task("Medium", duration=30),
    )
    scheduler = Scheduler(owner=owner)
    result = scheduler.sort_by_duration(scheduler.tasks, ascending=True)
    durations = [t.duration_minutes for t in result]
    assert durations == sorted(durations)


def test_sort_by_duration_descending():
    owner, _ = make_owner_with_pet(
        make_task("Long",  duration=60),
        make_task("Short", duration=10),
    )
    scheduler = Scheduler(owner=owner)
    result = scheduler.sort_by_duration(scheduler.tasks, ascending=False)
    assert result[0].duration_minutes == 60


def test_sort_by_duration_single_task():
    # Sorting a one-item list should not crash and should return that task.
    owner, _ = make_owner_with_pet(make_task("Only task", duration=20))
    scheduler = Scheduler(owner=owner)
    result = scheduler.sort_by_duration(scheduler.tasks)
    assert len(result) == 1


def test_sort_by_duration_empty_list():
    # Sorting an empty list should return an empty list without raising.
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])
    assert scheduler.sort_by_duration([]) == []


def test_sort_by_due_date_earliest_first():
    today = date.today()
    owner, pet = make_owner_with_pet()
    pet.add_task(Task("Later",  "other", 10, due_date=today + timedelta(days=3)))
    pet.add_task(Task("Sooner", "other", 10, due_date=today + timedelta(days=1)))
    scheduler = Scheduler(owner=owner)
    result = scheduler.sort_by_due_date(scheduler.tasks)
    assert result[0].description == "Sooner"


def test_sort_by_due_date_none_goes_last():
    # Tasks with no due_date should sort after tasks that have one.
    today = date.today()
    owner, pet = make_owner_with_pet()
    pet.add_task(Task("No date",   "other", 10))                          # due_date=None
    pet.add_task(Task("Has date",  "other", 10, due_date=today + timedelta(days=1)))
    scheduler = Scheduler(owner=owner)
    result = scheduler.sort_by_due_date(scheduler.tasks)
    assert result[0].description == "Has date"
    assert result[-1].description == "No date"


# ===========================================================================
# 4. Filtering
# ===========================================================================

def test_filter_by_pet_name_isolates_correct_tasks():
    owner = Owner(name="Jordan", available_minutes=120)
    mochi = Pet(name="Mochi", species="dog")
    luna  = Pet(name="Luna",  species="cat")
    mochi.add_task(make_task("Walk Mochi"))
    luna.add_task(make_task("Feed Luna"))
    owner.add_pet(mochi)
    owner.add_pet(luna)

    scheduler = Scheduler(owner=owner)
    result = scheduler.filter_tasks(scheduler.tasks, pet_name="Mochi")
    assert len(result) == 1
    assert result[0].description == "Walk Mochi"


def test_filter_by_pet_name_nonexistent_returns_empty():
    # Filtering by a pet that doesn't exist should return [] not crash.
    owner, _ = make_owner_with_pet(make_task("Walk"))
    scheduler = Scheduler(owner=owner)
    result = scheduler.filter_tasks(scheduler.tasks, pet_name="Ghost")
    assert result == []


def test_filter_completed_true():
    owner, pet = make_owner_with_pet(make_task("Done"), make_task("Pending"))
    pet.tasks[0].mark_complete()
    scheduler = Scheduler(owner=owner)
    result = scheduler.filter_tasks(scheduler.tasks, completed=True)
    assert len(result) == 1
    assert result[0].description == "Done"


def test_filter_completed_false():
    owner, pet = make_owner_with_pet(make_task("Done"), make_task("Pending"))
    pet.tasks[0].mark_complete()
    scheduler = Scheduler(owner=owner)
    result = scheduler.filter_tasks(scheduler.tasks, completed=False)
    assert len(result) == 1
    assert result[0].description == "Pending"


def test_filter_by_category():
    owner, pet = make_owner_with_pet()
    pet.add_task(Task("Walk",  "walk",    30))
    pet.add_task(Task("Feed",  "feeding", 10))
    pet.add_task(Task("Brush", "grooming", 15))
    scheduler = Scheduler(owner=owner)
    result = scheduler.filter_tasks(scheduler.tasks, category="walk")
    assert len(result) == 1
    assert result[0].description == "Walk"


def test_filter_no_match_returns_empty():
    owner, _ = make_owner_with_pet(make_task("Walk", category="walk"))
    scheduler = Scheduler(owner=owner)
    result = scheduler.filter_tasks(scheduler.tasks, category="medication")
    assert result == []


def test_filter_combined_pet_and_category():
    # Multiple filters should be ANDed together.
    owner = Owner(name="Jordan", available_minutes=120)
    mochi = Pet(name="Mochi", species="dog")
    luna  = Pet(name="Luna",  species="cat")
    mochi.add_task(Task("Walk Mochi", "walk",    30))
    mochi.add_task(Task("Feed Mochi", "feeding", 10))
    luna.add_task(Task("Feed Luna",   "feeding",  5))
    owner.add_pet(mochi)
    owner.add_pet(luna)

    scheduler = Scheduler(owner=owner)
    result = scheduler.filter_tasks(scheduler.tasks, pet_name="Mochi", category="feeding")
    assert len(result) == 1
    assert result[0].description == "Feed Mochi"


# ===========================================================================
# 5. Scheduler — schedule generation
# ===========================================================================

def test_scheduler_with_no_pets_returns_empty_schedule():
    # An owner with no pets attached should not crash the scheduler.
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner)
    assert scheduler.generate_schedule() == []


def test_scheduler_with_pet_with_no_tasks_returns_empty_schedule():
    owner = Owner(name="Jordan", available_minutes=120)
    owner.add_pet(Pet(name="Mochi", species="dog"))  # pet exists but has no tasks
    scheduler = Scheduler(owner=owner)
    assert scheduler.generate_schedule() == []


def test_scheduler_with_zero_available_time_returns_empty_schedule():
    # Edge case: owner has zero minutes — nothing should fit.
    owner, _ = make_owner_with_pet(make_task("Walk", duration=5), available_minutes=0)
    scheduler = Scheduler(owner=owner)
    assert scheduler.generate_schedule() == []


def test_scheduler_task_exactly_fills_budget_is_included():
    # A task whose duration == available_minutes should be scheduled, not dropped.
    owner, _ = make_owner_with_pet(make_task("Long walk", duration=60), available_minutes=60)
    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()
    assert len(schedule) == 1
    assert schedule[0].task.description == "Long walk"


def test_scheduler_task_one_minute_over_budget_is_excluded():
    # A task 1 min longer than the budget must not be scheduled.
    owner, _ = make_owner_with_pet(make_task("Too long", duration=61), available_minutes=60)
    scheduler = Scheduler(owner=owner)
    assert scheduler.generate_schedule() == []


def test_scheduler_respects_time_budget():
    owner, _ = make_owner_with_pet(
        make_task("Walk", duration=20, priority=Priority.HIGH),
        make_task("Play", duration=20, priority=Priority.MEDIUM),
        available_minutes=30,
    )
    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()
    total = sum(e.task.duration_minutes for e in schedule)
    assert total <= 30


def test_scheduler_prioritises_high_over_low():
    # When only one task fits, it must be the high-priority one.
    owner, _ = make_owner_with_pet(
        make_task("Low task",  duration=15, priority=Priority.LOW),
        make_task("High task", duration=15, priority=Priority.HIGH),
        available_minutes=20,
    )
    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()
    assert len(schedule) == 1
    assert schedule[0].task.priority == Priority.HIGH


def test_scheduler_all_tasks_same_priority_schedules_in_order():
    # When priorities are equal, the order they were added should be preserved.
    owner, _ = make_owner_with_pet(
        make_task("First",  duration=10, priority=Priority.MEDIUM),
        make_task("Second", duration=10, priority=Priority.MEDIUM),
        available_minutes=120,
    )
    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()
    assert schedule[0].task.description == "First"
    assert schedule[1].task.description == "Second"


def test_completed_tasks_excluded_from_schedule():
    done = make_task("Already done", duration=10, priority=Priority.HIGH)
    done.mark_complete()
    pending = make_task("Still to do", duration=10, priority=Priority.MEDIUM)
    owner, _ = make_owner_with_pet(done, pending)
    scheduler = Scheduler(owner=owner)
    descriptions = [e.task.description for e in scheduler.generate_schedule()]
    assert "Already done" not in descriptions
    assert "Still to do" in descriptions


def test_all_tasks_completed_returns_empty_schedule():
    # If every task is already done, the schedule should be empty.
    t1 = make_task("Walk")
    t2 = make_task("Feed")
    t1.mark_complete()
    t2.mark_complete()
    owner, _ = make_owner_with_pet(t1, t2)
    scheduler = Scheduler(owner=owner)
    assert scheduler.generate_schedule() == []


# ===========================================================================
# 5b. Recurring renewal via Scheduler
# ===========================================================================

def test_mark_task_complete_renews_daily_task():
    today = date.today()
    owner, pet = make_owner_with_pet(
        Task("Morning walk", "walk", 30, frequency="daily", due_date=today)
    )
    scheduler = Scheduler(owner=owner)
    task = pet.tasks[0]
    renewal = scheduler.mark_task_complete(task, pet)

    assert task.is_completed is True
    assert renewal is not None
    assert renewal.due_date == today + timedelta(days=1)
    assert len(pet.tasks) == 2  # original (done) + renewal


def test_mark_task_complete_renews_weekly_task():
    today = date.today()
    owner, pet = make_owner_with_pet(
        Task("Flea meds", "medication", 5, frequency="weekly", due_date=today)
    )
    scheduler = Scheduler(owner=owner)
    renewal = scheduler.mark_task_complete(pet.tasks[0], pet)
    assert renewal.due_date == today + timedelta(days=7)


def test_mark_task_complete_does_not_renew_as_needed():
    owner, pet = make_owner_with_pet(
        Task("Vet visit", "medication", 60, frequency="as-needed")
    )
    scheduler = Scheduler(owner=owner)
    renewal = scheduler.mark_task_complete(pet.tasks[0], pet)
    assert renewal is None
    assert len(pet.tasks) == 1  # no new task added


def test_renewal_is_not_yet_completed():
    # The freshly created renewal should be pending, not already done.
    today = date.today()
    owner, pet = make_owner_with_pet(
        Task("Walk", "walk", 20, frequency="daily", due_date=today)
    )
    scheduler = Scheduler(owner=owner)
    renewal = scheduler.mark_task_complete(pet.tasks[0], pet)
    assert renewal.is_completed is False


# ===========================================================================
# 5c. Conflict detection
# ===========================================================================

def test_detect_conflicts_clean_schedule():
    # Back-to-back slots (A ends exactly when B starts) must not be flagged.
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])
    a = ScheduledTask(task=make_task("A", duration=10), pet_name="Mochi", start_minute=0,  reason="")
    b = ScheduledTask(task=make_task("B", duration=15), pet_name="Mochi", start_minute=10, reason="")
    assert scheduler.detect_conflicts([a, b]) == []


def test_detect_conflicts_finds_overlap():
    # A: 0–30, B: 20–40  → 10-minute overlap, one warning expected.
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])
    a = ScheduledTask(task=make_task("Task A", duration=30), pet_name="Mochi", start_minute=0,  reason="")
    b = ScheduledTask(task=make_task("Task B", duration=20), pet_name="Luna",  start_minute=20, reason="")
    warnings = scheduler.detect_conflicts([a, b])
    assert len(warnings) == 1
    assert "Task A" in warnings[0] and "Task B" in warnings[0]


def test_detect_conflicts_same_start_time():
    # Two tasks starting at the same minute are always a conflict.
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])
    a = ScheduledTask(task=make_task("A", duration=20), pet_name="Mochi", start_minute=0, reason="")
    b = ScheduledTask(task=make_task("B", duration=20), pet_name="Luna",  start_minute=0, reason="")
    warnings = scheduler.detect_conflicts([a, b])
    assert len(warnings) == 1


def test_detect_conflicts_multiple_pairs():
    # Three mutually-overlapping tasks should produce three conflict warnings (C(3,2)=3).
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])
    a = ScheduledTask(task=make_task("A", duration=30), pet_name="P1", start_minute=0,  reason="")
    b = ScheduledTask(task=make_task("B", duration=30), pet_name="P2", start_minute=10, reason="")
    c = ScheduledTask(task=make_task("C", duration=30), pet_name="P3", start_minute=20, reason="")
    warnings = scheduler.detect_conflicts([a, b, c])
    assert len(warnings) == 3


def test_detect_conflicts_empty_schedule():
    # No entries → no warnings (should not raise).
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])
    assert scheduler.detect_conflicts([]) == []


def test_detect_conflicts_single_entry():
    # A single entry can never conflict with itself.
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])
    a = ScheduledTask(task=make_task("Solo", duration=20), pet_name="Mochi", start_minute=0, reason="")
    assert scheduler.detect_conflicts([a]) == []


def test_normal_generated_schedule_has_no_conflicts():
    # The greedy scheduler must produce a conflict-free schedule.
    owner, _ = make_owner_with_pet(
        make_task("Walk",  duration=30, priority=Priority.HIGH),
        make_task("Feed",  duration=10, priority=Priority.HIGH),
        make_task("Brush", duration=15, priority=Priority.LOW),
    )
    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()
    assert scheduler.detect_conflicts(schedule) == []
