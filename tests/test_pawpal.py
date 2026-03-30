from datetime import date, timedelta

from pawpal_system import Owner, Pet, Priority, ScheduledTask, Scheduler, Task


def make_task(description="Test task", duration=15, priority=Priority.MEDIUM, frequency="daily"):
    """Helper to build a Task without repeating boilerplate in every test."""
    return Task(
        description=description,
        category="other",
        duration_minutes=duration,
        priority=priority,
        frequency=frequency,
    )


def make_owner_with_pet(*tasks):
    """Build an Owner with a single Pet that has the given tasks attached."""
    owner = Owner(name="Jordan", available_minutes=120)
    pet = Pet(name="Mochi", species="dog")
    for t in tasks:
        pet.add_task(t)
    owner.add_pet(pet)
    return owner, pet


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    task = make_task("Give flea medication")
    assert task.is_completed is False
    task.mark_complete()
    assert task.is_completed is True


def test_mark_complete_does_not_affect_other_tasks():
    t1 = make_task("Walk")
    t2 = make_task("Feed")
    t1.mark_complete()
    assert t1.is_completed is True
    assert t2.is_completed is False


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


def test_next_occurrence_as_needed_returns_none():
    task = Task("Vet visit", "medication", 60, frequency="as-needed")
    assert task.next_occurrence() is None


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

def test_add_task_increases_pet_task_count():
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0
    pet.add_task(make_task("Morning walk"))
    assert len(pet.tasks) == 1
    pet.add_task(make_task("Feeding"))
    assert len(pet.tasks) == 2


def test_remove_task_decreases_pet_task_count():
    pet = Pet(name="Luna", species="cat")
    task = make_task("Brush coat")
    pet.add_task(task)
    assert len(pet.tasks) == 1
    pet.remove_task(task)
    assert len(pet.tasks) == 0


def test_pending_tasks_excludes_completed():
    pet = Pet(name="Mochi", species="dog")
    done = make_task("Old walk")
    done.mark_complete()
    pending = make_task("Evening walk")
    pet.add_task(done)
    pet.add_task(pending)
    assert len(pet.pending_tasks()) == 1
    assert pet.pending_tasks()[0].description == "Evening walk"


# ---------------------------------------------------------------------------
# Sorting tests
# ---------------------------------------------------------------------------

def test_sort_by_duration_ascending():
    owner, pet = make_owner_with_pet(
        make_task("Long task",   duration=60),
        make_task("Short task",  duration=10),
        make_task("Medium task", duration=30),
    )
    scheduler = Scheduler(owner=owner)
    sorted_tasks = scheduler.sort_by_duration(scheduler.tasks, ascending=True)
    durations = [t.duration_minutes for t in sorted_tasks]
    assert durations == sorted(durations)


def test_sort_by_duration_descending():
    owner, pet = make_owner_with_pet(
        make_task("Long task",   duration=60),
        make_task("Short task",  duration=10),
    )
    scheduler = Scheduler(owner=owner)
    sorted_tasks = scheduler.sort_by_duration(scheduler.tasks, ascending=False)
    assert sorted_tasks[0].duration_minutes == 60


def test_sort_by_due_date_earliest_first():
    today = date.today()
    owner, pet = make_owner_with_pet()
    pet.add_task(Task("Later task",  "other", 10, due_date=today + timedelta(days=3)))
    pet.add_task(Task("Sooner task", "other", 10, due_date=today + timedelta(days=1)))
    scheduler = Scheduler(owner=owner)
    sorted_tasks = scheduler.sort_by_due_date(scheduler.tasks)
    assert sorted_tasks[0].description == "Sooner task"


# ---------------------------------------------------------------------------
# Filtering tests
# ---------------------------------------------------------------------------

def test_filter_by_pet_name():
    owner = Owner(name="Jordan", available_minutes=120)
    mochi = Pet(name="Mochi", species="dog")
    luna = Pet(name="Luna", species="cat")
    mochi.add_task(make_task("Walk"))
    luna.add_task(make_task("Feed luna"))
    owner.add_pet(mochi)
    owner.add_pet(luna)

    scheduler = Scheduler(owner=owner)
    mochi_tasks = scheduler.filter_tasks(scheduler.tasks, pet_name="Mochi")
    assert all(t.description == "Walk" for t in mochi_tasks)
    assert len(mochi_tasks) == 1


def test_filter_by_completed_status():
    owner, pet = make_owner_with_pet(make_task("Done task"), make_task("Pending task"))
    pet.tasks[0].mark_complete()
    scheduler = Scheduler(owner=owner)

    done = scheduler.filter_tasks(scheduler.tasks, completed=True)
    pending = scheduler.filter_tasks(scheduler.tasks, completed=False)
    assert len(done) == 1
    assert len(pending) == 1
    assert done[0].description == "Done task"


def test_filter_by_category():
    owner, pet = make_owner_with_pet()
    pet.add_task(Task("Walk Mochi", "walk", 30))
    pet.add_task(Task("Feed Mochi", "feeding", 10))
    scheduler = Scheduler(owner=owner)

    walks = scheduler.filter_tasks(scheduler.tasks, category="walk")
    assert len(walks) == 1
    assert walks[0].description == "Walk Mochi"


# ---------------------------------------------------------------------------
# Recurring task renewal tests
# ---------------------------------------------------------------------------

def test_mark_task_complete_renews_daily_task():
    owner, pet = make_owner_with_pet(
        Task("Morning walk", "walk", 30, frequency="daily", due_date=date.today())
    )
    scheduler = Scheduler(owner=owner)
    task = pet.tasks[0]
    renewal = scheduler.mark_task_complete(task, pet)

    assert task.is_completed is True
    assert renewal is not None
    assert renewal.due_date == date.today() + timedelta(days=1)
    assert len(pet.tasks) == 2  # original (done) + renewal


def test_mark_task_complete_does_not_renew_as_needed():
    owner, pet = make_owner_with_pet(
        Task("Vet visit", "medication", 60, frequency="as-needed")
    )
    scheduler = Scheduler(owner=owner)
    task = pet.tasks[0]
    renewal = scheduler.mark_task_complete(task, pet)

    assert task.is_completed is True
    assert renewal is None
    assert len(pet.tasks) == 1  # no new task added


# ---------------------------------------------------------------------------
# Conflict detection tests
# ---------------------------------------------------------------------------

def test_detect_conflicts_finds_overlap():
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])

    # A: 0–30, B: 20–40 — overlap from 20 to 30
    a = ScheduledTask(task=make_task("Task A", duration=30), pet_name="Mochi", start_minute=0,  reason="")
    b = ScheduledTask(task=make_task("Task B", duration=20), pet_name="Luna",  start_minute=20, reason="")

    warnings = scheduler.detect_conflicts([a, b])
    assert len(warnings) == 1
    assert "Task A" in warnings[0]
    assert "Task B" in warnings[0]


def test_detect_conflicts_clean_schedule():
    owner = Owner(name="Jordan", available_minutes=120)
    scheduler = Scheduler(owner=owner, tasks=[])

    # A: 0–10, B: 10–25 — back to back, no overlap
    a = ScheduledTask(task=make_task("Task A", duration=10), pet_name="Mochi", start_minute=0,  reason="")
    b = ScheduledTask(task=make_task("Task B", duration=15), pet_name="Mochi", start_minute=10, reason="")

    warnings = scheduler.detect_conflicts([a, b])
    assert warnings == []


# ---------------------------------------------------------------------------
# Original scheduler tests
# ---------------------------------------------------------------------------

def test_scheduler_respects_time_budget():
    owner, pet = make_owner_with_pet(
        make_task("Walk", duration=20, priority=Priority.HIGH),
        make_task("Play", duration=20, priority=Priority.MEDIUM),
    )
    owner.available_minutes = 30

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    total_minutes = sum(e.task.duration_minutes for e in schedule)
    assert total_minutes <= 30


def test_scheduler_prioritises_high_over_low():
    owner, pet = make_owner_with_pet(
        make_task("Low priority task",  duration=15, priority=Priority.LOW),
        make_task("High priority task", duration=15, priority=Priority.HIGH),
    )
    owner.available_minutes = 20

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    assert len(schedule) == 1
    assert schedule[0].task.priority == Priority.HIGH


def test_completed_tasks_are_skipped():
    done = make_task("Already done", duration=10, priority=Priority.HIGH)
    done.mark_complete()
    pending = make_task("Still to do", duration=10, priority=Priority.MEDIUM)
    owner, pet = make_owner_with_pet(done, pending)

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    descriptions = [e.task.description for e in schedule]
    assert "Already done" not in descriptions
    assert "Still to do" in descriptions
