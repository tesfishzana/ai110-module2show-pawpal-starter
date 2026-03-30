from dataclasses import dataclass, field
from datetime import date, timedelta
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
    due_date: Optional[date] = None  # None means "today" when not explicitly set

    def mark_complete(self) -> None:
        """Flip the task to completed."""
        self.is_completed = True

    def next_occurrence(self) -> Optional["Task"]:
        """
        Return a fresh copy of this task scheduled for its next occurrence.
        Returns None for as-needed tasks because there's no predictable next date.
        """
        if self.frequency == "as-needed":
            return None

        base = self.due_date if self.due_date else date.today()
        delta = timedelta(days=1 if self.frequency == "daily" else 7)

        return Task(
            description=self.description,
            category=self.category,
            duration_minutes=self.duration_minutes,
            frequency=self.frequency,
            priority=self.priority,
            due_date=base + delta,
        )

    def __str__(self) -> str:
        status = "done" if self.is_completed else self.priority.value
        due = f", due {self.due_date}" if self.due_date else ""
        return f"[{status.upper()}] {self.description} ({self.duration_minutes} min, {self.frequency}{due})"


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

    Generates a greedy daily care schedule, but also provides sorting,
    filtering, recurring task renewal, and conflict detection.
    """

    def __init__(
        self,
        owner: Owner,
        pet: Optional[Pet] = None,
        tasks: Optional[List[Task]] = None,
    ):
        self.owner = owner
        self.pet = pet

        if tasks is not None:
            self.tasks = tasks
        elif pet is not None:
            self.tasks = list(pet.tasks)
        else:
            self.tasks = self.get_all_tasks()

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_all_tasks(self) -> List[Task]:
        """Retrieve every task across all of the owner's pets."""
        return self.owner.get_all_tasks()

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_by_duration(self, tasks: List[Task], ascending: bool = True) -> List[Task]:
        """Sort tasks by duration in minutes, shortest first by default."""
        return sorted(tasks, key=lambda t: t.duration_minutes, reverse=not ascending)

    def sort_by_due_date(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by due date, earliest first. Tasks without a due date go last."""
        return sorted(tasks, key=lambda t: t.due_date or date.max)

    def filter_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Sort pending tasks from highest to lowest priority."""
        return sorted(
            [t for t in tasks if not t.is_completed],
            key=lambda t: _PRIORITY_RANK[t.priority],
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_tasks(
        self,
        tasks: List[Task],
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> List[Task]:
        """
        Filter a task list by one or more criteria.

        pet_name  — keep only tasks belonging to this pet
        completed — True for done tasks, False for pending, None for all
        category  — keep only tasks in this category (e.g. "walk", "feeding")
        """
        result = list(tasks)

        if pet_name is not None:
            # Build the set of task ids owned by the named pet
            owned_ids = {
                id(t)
                for p in self.owner.pets if p.name == pet_name
                for t in p.tasks
            }
            result = [t for t in result if id(t) in owned_ids]

        if completed is not None:
            result = [t for t in result if t.is_completed == completed]

        if category is not None:
            result = [t for t in result if t.category == category]

        return result

    # ------------------------------------------------------------------
    # Recurring task renewal
    # ------------------------------------------------------------------

    def mark_task_complete(self, task: Task, pet: Pet) -> Optional[Task]:
        """
        Mark a task as done and automatically queue the next occurrence
        if the task is recurring (daily or weekly).

        Returns the newly created Task, or None for as-needed tasks.
        """
        task.mark_complete()
        renewal = task.next_occurrence()
        if renewal:
            pet.add_task(renewal)
        return renewal

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(self, schedule: List[ScheduledTask]) -> List[str]:
        """
        Scan a schedule for overlapping time slots.

        Two entries conflict when one starts before the other ends — the
        classic interval overlap check: A.start < B.end AND B.start < A.end.
        Returns a list of human-readable warning strings (empty if no conflicts).
        """
        warnings = []
        for i, a in enumerate(schedule):
            for b in schedule[i + 1:]:
                if a.start_minute < b.end_minute and b.start_minute < a.end_minute:
                    warnings.append(
                        f"  ! CONFLICT: '{a.task.description}' ({a.time_label()}) "
                        f"overlaps '{b.task.description}' ({b.time_label()})"
                    )
        return warnings

    # ------------------------------------------------------------------
    # Schedule generation
    # ------------------------------------------------------------------

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
        skipped = [t for t in self.tasks if id(t) not in scheduled_ids and not t.is_completed]
        if skipped:
            lines.append("\nSkipped (didn't fit in the time budget):")
            for t in skipped:
                lines.append(f"  x  {t.description} — {t.duration_minutes} min ({t.priority.value})")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

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
