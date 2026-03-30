from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Higher number = lower urgency. Used for sorting.
_PRIORITY_RANK = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


@dataclass
class Task:
    """A single care activity for a pet."""

    description: str          # what needs to happen, e.g. "morning walk"
    category: str             # broad type: "walk", "feeding", "medication", "grooming", etc.
    duration_minutes: int     # how long this realistically takes
    frequency: str = "daily"  # how often: "daily", "weekly", "as-needed"
    priority: Priority = Priority.MEDIUM
    is_completed: bool = False

    def mark_complete(self) -> None:
        """Flip the task to completed."""
        self.is_completed = True

    def __str__(self) -> str:
        status = "done" if self.is_completed else self.priority.value
        return f"[{status.upper()}] {self.description} ({self.duration_minutes} min, {self.frequency})"


@dataclass
class Pet:
    """A pet with its own list of care tasks."""

    name: str
    species: str        # "dog", "cat", "rabbit", "bird", etc.
    age_years: int = 0
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet's list."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a specific task from this pet's list."""
        self.tasks = [t for t in self.tasks if t is not task]

    def pending_tasks(self) -> List[Task]:
        """Return only tasks that haven't been completed yet."""
        return [t for t in self.tasks if not t.is_completed]

    def __str__(self) -> str:
        return f"{self.name} the {self.species} (age {self.age_years})"


@dataclass
class Owner:
    """The pet owner — holds the time budget and all their pets."""

    name: str
    available_minutes: int = 120
    preferences: List[str] = field(default_factory=list)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def set_available_time(self, minutes: int) -> None:
        """Update how many minutes the owner has free today."""
        self.available_minutes = minutes

    def get_all_tasks(self) -> List[Task]:
        """Collect every task from every pet this owner has."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    def __str__(self) -> str:
        pet_names = ", ".join(p.name for p in self.pets) if self.pets else "no pets yet"
        return f"{self.name} ({self.available_minutes} min available | pets: {pet_names})"


@dataclass
class ScheduledTask:
    """One task placed at a concrete time slot in the day."""

    task: Task
    pet_name: str        # which pet this task belongs to
    start_minute: int    # offset in minutes from the start of the day window
    reason: str

    @property
    def end_minute(self) -> int:
        """Minute offset when this task finishes."""
        return self.start_minute + self.task.duration_minutes

    def time_label(self, day_start_hour: int = 8) -> str:
        """Format the slot as a readable string like '08:00 – 08:20'."""
        def fmt(offset: int) -> str:
            h = day_start_hour + offset // 60
            m = offset % 60
            return f"{h:02d}:{m:02d}"
        return f"{fmt(self.start_minute)} – {fmt(self.end_minute)}"


class Scheduler:
    """
    The brain of PawPal+.

    It asks the Owner for all pet tasks, sorts them by priority, and greedily
    fits as many as possible into the owner's available time for the day.
    Tasks that don't fit are listed as skipped at the end of the explanation.
    """

    def __init__(
        self,
        owner: Owner,
        pet: Optional[Pet] = None,
        tasks: Optional[List[Task]] = None,
    ):
        self.owner = owner
        # If a specific pet is passed, use it for display labels.
        # Otherwise we're working across all the owner's pets.
        self.pet = pet

        if tasks is not None:
            # Explicit override — used by the UI when it manages its own task list.
            self.tasks = tasks
        elif pet is not None:
            # Single-pet mode: just that pet's tasks.
            self.tasks = list(pet.tasks)
        else:
            # Normal mode: ask the Owner to gather tasks from all their pets.
            self.tasks = self.get_all_tasks()

    def get_all_tasks(self) -> List[Task]:
        """Retrieve every task across all of the owner's pets."""
        return self.owner.get_all_tasks()

    def filter_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Sort pending tasks from highest to lowest priority."""
        return sorted(
            [t for t in tasks if not t.is_completed],
            key=lambda t: _PRIORITY_RANK[t.priority],
        )

    def generate_schedule(self) -> List[ScheduledTask]:
        """
        Build the day's plan.

        Walks through tasks in priority order and slots each one in if it fits
        the remaining time budget. Simple greedy approach — works well enough
        for daily pet care where missing a high-priority task is the main risk.
        """
        sorted_tasks = self.filter_by_priority(self.tasks)
        schedule: List[ScheduledTask] = []
        time_used = 0
        budget = self.owner.available_minutes

        for task in sorted_tasks:
            if time_used + task.duration_minutes <= budget:
                pet_name = self._find_pet_name(task)
                reason = self._build_reason(task, time_used, budget)
                schedule.append(
                    ScheduledTask(
                        task=task,
                        pet_name=pet_name,
                        start_minute=time_used,
                        reason=reason,
                    )
                )
                time_used += task.duration_minutes

        return schedule

    def explain_plan(self, schedule: List[ScheduledTask]) -> str:
        """Return a plain-English summary of the schedule and anything that didn't fit."""
        if not schedule:
            return "Nothing could be scheduled — either no tasks exist or none fit the time budget."

        pet_label = self.pet.name if self.pet else "all pets"
        lines = [
            f"Today's plan for {pet_label}",
            f"Owner: {self.owner.name}  |  Budget: {self.owner.available_minutes} min",
            "-" * 50,
        ]

        for i, entry in enumerate(schedule, 1):
            lines.append(f"{i}. {entry.time_label()}  {entry.task.description}  ({entry.pet_name})")
            lines.append(f"   {entry.reason}")

        total = sum(e.task.duration_minutes for e in schedule)
        lines.append("-" * 50)
        lines.append(f"Total: {total} min used of {self.owner.available_minutes} min available.")

        scheduled_ids = {id(e.task) for e in schedule}
        skipped = [t for t in self.tasks if id(t) not in scheduled_ids]
        if skipped:
            lines.append("\nSkipped (didn't fit in the time budget):")
            for t in skipped:
                lines.append(f"  x  {t.description} — {t.duration_minutes} min ({t.priority.value})")

        return "\n".join(lines)

    def _find_pet_name(self, task: Task) -> str:
        """Look up which pet owns this task, falling back to a generic label."""
        if self.pet:
            return self.pet.name
        for pet in self.owner.pets:
            if task in pet.tasks:
                return pet.name
        return "unknown"

    def _build_reason(self, task: Task, time_used: int, budget: int) -> str:
        """Explain in one sentence why this task made it into the schedule."""
        remaining = budget - time_used
        note = {
            Priority.HIGH:   "High priority — goes in first",
            Priority.MEDIUM: "Medium priority — fits the available window",
            Priority.LOW:    "Low priority — there's room, so why not",
        }[task.priority]
        return f"{note}. ({task.duration_minutes} min needed, {remaining} min left)"
