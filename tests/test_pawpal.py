from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def make_task(description="Test task", duration=15, priority=Priority.MEDIUM):
    """Helper to build a Task without repeating boilerplate in every test."""
    return Task(description=description, category="other", duration_minutes=duration, priority=priority)


# --- Task tests ---

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
    assert t2.is_completed is False  # t2 should be untouched


# --- Pet tests ---

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


# --- Scheduler tests ---

def test_scheduler_respects_time_budget():
    owner = Owner(name="Jordan", available_minutes=30)
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(make_task("Walk", duration=20, priority=Priority.HIGH))
    pet.add_task(make_task("Play", duration=20, priority=Priority.MEDIUM))  # won't fit
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    total_minutes = sum(e.task.duration_minutes for e in schedule)
    assert total_minutes <= 30


def test_scheduler_prioritises_high_over_low():
    owner = Owner(name="Jordan", available_minutes=20)
    pet = Pet(name="Mochi", species="dog")
    pet.add_task(make_task("Low priority task", duration=15, priority=Priority.LOW))
    pet.add_task(make_task("High priority task", duration=15, priority=Priority.HIGH))
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    assert len(schedule) == 1
    assert schedule[0].task.priority == Priority.HIGH


def test_completed_tasks_are_skipped():
    owner = Owner(name="Jordan", available_minutes=60)
    pet = Pet(name="Mochi", species="dog")
    done = make_task("Already done", duration=10, priority=Priority.HIGH)
    done.mark_complete()
    pending = make_task("Still to do", duration=10, priority=Priority.MEDIUM)
    pet.add_task(done)
    pet.add_task(pending)
    owner.add_pet(pet)

    scheduler = Scheduler(owner=owner)
    schedule = scheduler.generate_schedule()

    descriptions = [e.task.description for e in schedule]
    assert "Already done" not in descriptions
    assert "Still to do" in descriptions
