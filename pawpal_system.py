"""
PawPal+ — backend logic layer.

Classes:
    Task      — a single pet care task (dataclass)
    Pet       — a pet with a list of tasks (dataclass)
    Owner     — the pet owner with time budget (dataclass)
    Scheduler — builds and explains a daily care plan
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Priority enum
# ---------------------------------------------------------------------------

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet care task."""

    title: str
    category: str          # e.g. "walk", "feeding", "medication", "grooming"
    duration_minutes: int
    priority: Priority = Priority.MEDIUM
    is_completed: bool = False

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.is_completed = True

    def __str__(self) -> str:
        return f"[{self.priority.value.upper()}] {self.title} ({self.duration_minutes} min)"


@dataclass
class Pet:
    """A pet owned by an Owner."""

    name: str
    species: str           # "dog", "cat", "rabbit", …
    age_years: int = 0
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's list."""
        self.tasks = [t for t in self.tasks if t is not task]

    def __str__(self) -> str:
        return f"{self.name} ({self.species}, {self.age_years}y)"


@dataclass
class Owner:
    """The pet owner who has a daily time budget."""

    name: str
    available_minutes: int = 120
    preferences: List[str] = field(default_factory=list)  # e.g. ["no meds before breakfast"]
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's household."""
        self.pets.append(pet)

    def set_available_time(self, minutes: int) -> None:
        """Update how much time the owner has today."""
        self.available_minutes = minutes

    def __str__(self) -> str:
        return f"{self.name} ({self.available_minutes} min available)"


# ---------------------------------------------------------------------------
# Scheduled result
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A task placed at a specific time in the daily plan."""

    task: Task
    start_minute: int   # minutes from the start of the day window
    reason: str

    @property
    def end_minute(self) -> int:
        return self.start_minute + self.task.duration_minutes

    def time_label(self, day_start_hour: int = 8) -> str:
        """Return a human-readable time range, e.g. '08:00 – 08:20'."""
        def fmt(minutes: int) -> str:
            h = day_start_hour + minutes // 60
            m = minutes % 60
            return f"{h:02d}:{m:02d}"
        return f"{fmt(self.start_minute)} – {fmt(self.end_minute)}"


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """
    Builds a greedy daily care schedule.

    Strategy:
        1. Sort tasks by priority (high → medium → low), skipping completed ones.
        2. Walk through tasks in order; include each task if it fits in the
           remaining time budget.
        3. Continue scanning for smaller tasks that might still fit even after
           a large task was skipped.
    """

    def __init__(
        self,
        owner: Owner,
        pet: Pet,
        tasks: Optional[List[Task]] = None,
    ):
        self.owner = owner
        self.pet = pet
        # Use explicitly passed tasks or fall back to the pet's own task list.
        self.tasks: List[Task] = tasks if tasks is not None else list(pet.tasks)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Return non-completed tasks sorted high → medium → low."""
        return sorted(
            [t for t in tasks if not t.is_completed],
            key=lambda t: _PRIORITY_ORDER[t.priority],
        )

    def generate_schedule(self) -> List[ScheduledTask]:
        """
        Produce an ordered list of ScheduledTask entries that fit within the
        owner's available time.
        """
        sorted_tasks = self.filter_by_priority(self.tasks)
        schedule: List[ScheduledTask] = []
        time_used = 0
        budget = self.owner.available_minutes

        for task in sorted_tasks:
            if time_used + task.duration_minutes <= budget:
                reason = self._build_reason(task, time_used, budget)
                schedule.append(
                    ScheduledTask(task=task, start_minute=time_used, reason=reason)
                )
                time_used += task.duration_minutes

        return schedule

    def explain_plan(self, schedule: List[ScheduledTask]) -> str:
        """Return a multi-line text explanation of the generated schedule."""
        if not schedule:
            return "No tasks could be scheduled within the available time."

        lines = [
            f"Daily plan for {self.pet.name}",
            f"Owner: {self.owner.name} | Budget: {self.owner.available_minutes} min",
            "",
        ]
        for i, entry in enumerate(schedule, 1):
            lines.append(f"  {i}. {entry.time_label()} — {entry.task.title}")
            lines.append(f"     {entry.reason}")

        total = sum(e.task.duration_minutes for e in schedule)
        lines.append(f"\nTotal scheduled: {total} of {self.owner.available_minutes} min.")

        scheduled_tasks = {id(e.task) for e in schedule}
        skipped = [t for t in self.tasks if id(t) not in scheduled_tasks]
        if skipped:
            lines.append("\nNot scheduled (time constraint):")
            for t in skipped:
                lines.append(f"  - {t.title} ({t.duration_minutes} min, {t.priority.value})")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_reason(self, task: Task, time_used: int, budget: int) -> str:
        remaining = budget - time_used
        note = {
            Priority.HIGH: "High-priority — scheduled first",
            Priority.MEDIUM: "Medium-priority — fits within available time",
            Priority.LOW: "Low-priority — included because time allows",
        }[task.priority]
        return f"{note} ({task.duration_minutes} min needed, {remaining} min remaining)"
