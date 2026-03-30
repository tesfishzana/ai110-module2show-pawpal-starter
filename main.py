"""
main.py — quick demo to verify PawPal+ logic works before touching the UI.

Run with:  python main.py
"""

from pawpal_system import Owner, Pet, Priority, Scheduler, Task


def main():
    # Set up the owner with 2 hours free today
    jordan = Owner(name="Jordan", available_minutes=120)

    # Two pets with different needs
    mochi = Pet(name="Mochi", species="dog", age_years=3)
    luna = Pet(name="Luna", species="cat", age_years=5)

    # Mochi's tasks
    mochi.add_task(Task(
        description="Morning walk",
        category="walk",
        duration_minutes=30,
        frequency="daily",
        priority=Priority.HIGH,
    ))
    mochi.add_task(Task(
        description="Breakfast feeding",
        category="feeding",
        duration_minutes=10,
        frequency="daily",
        priority=Priority.HIGH,
    ))
    mochi.add_task(Task(
        description="Flea medication",
        category="medication",
        duration_minutes=5,
        frequency="weekly",
        priority=Priority.MEDIUM,
    ))
    mochi.add_task(Task(
        description="Fetch in the yard",
        category="enrichment",
        duration_minutes=20,
        frequency="daily",
        priority=Priority.LOW,
    ))

    # Luna's tasks
    luna.add_task(Task(
        description="Feed wet food",
        category="feeding",
        duration_minutes=5,
        frequency="daily",
        priority=Priority.HIGH,
    ))
    luna.add_task(Task(
        description="Clean litter box",
        category="grooming",
        duration_minutes=10,
        frequency="daily",
        priority=Priority.MEDIUM,
    ))
    luna.add_task(Task(
        description="Brush coat",
        category="grooming",
        duration_minutes=15,
        frequency="weekly",
        priority=Priority.LOW,
    ))

    # Register both pets with the owner
    jordan.add_pet(mochi)
    jordan.add_pet(luna)

    # Build the schedule — Scheduler pulls tasks from owner.pets automatically
    scheduler = Scheduler(owner=jordan)
    schedule = scheduler.generate_schedule()

    # Print Today's Schedule
    print("\n" + "=" * 55)
    print("  PAWPAL+ — TODAY'S SCHEDULE")
    print("=" * 55)

    if not schedule:
        print("Nothing scheduled — check available time or task durations.")
    else:
        for entry in schedule:
            print(f"  {entry.time_label()}  |  {entry.pet_name:<6}  |  {entry.task.description}")

    print("=" * 55)

    # Full explanation with reasons and skipped tasks
    print("\n" + scheduler.explain_plan(schedule))


if __name__ == "__main__":
    main()
