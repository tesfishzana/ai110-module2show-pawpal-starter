import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Used for the standard greedy scheduler (lower = higher urgency).
_PRIORITY_RANK = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}

# Used for the weighted scorer (higher = more important).
_PRIORITY_SCORE = {Priority.HIGH: 30, Priority.MEDIUM: 20, Priority.LOW: 10}

# Default category weights for the weighted scheduler.
# Medication and feeding are critical; grooming and enrichment are nice-to-have.
_DEFAULT_CATEGORY_WEIGHTS: Dict[str, int] = {
    "medication": 10,
    "feeding": 8,
    "walk": 5,
    "grooming": 3,
    "enrichment": 2,
    "other": 1,
}


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class Task:
    """A single care activity for a pet."""

    description: str
    category: str
    duration_minutes: int
    frequency: str = "daily"
    priority: Priority = Priority.MEDIUM
    is_completed: bool = False
    due_date: Optional[date] = None

    def mark_complete(self) -> None:
        """Flip the task to completed."""
        self.is_completed = True

    def next_occurrence(self) -> Optional["Task"]:
        """Return a fresh copy due at the next occurrence, or None for as-needed tasks."""
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

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary suitable for JSON output."""
        return {
            "description": self.description,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "frequency": self.frequency,
            "priority": self.priority.value,
            "is_completed": self.is_completed,
            "due_date": self.due_date.isoformat() if self.due_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Reconstruct a Task from a dictionary (e.g. loaded from JSON)."""
        due_raw = data.get("due_date")
        return cls(
            description=data["description"],
            category=data["category"],
            duration_minutes=data["duration_minutes"],
            frequency=data.get("frequency", "daily"),
            priority=Priority(data.get("priority", "medium")),
            is_completed=data.get("is_completed", False),
            due_date=date.fromisoformat(due_raw) if due_raw else None,
        )

    def __str__(self) -> str:
        status = "done" if self.is_completed else self.priority.value
        due = f", due {self.due_date}" if self.due_date else ""
        return f"[{status.upper()}] {self.description} ({self.duration_minutes} min, {self.frequency}{due})"


@dataclass
class Pet:
    """A pet with its own list of care tasks."""

    name: str
    species: str
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

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {
            "name": self.name,
            "species": self.species,
            "age_years": self.age_years,
            "tasks": [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pet":
        """Reconstruct a Pet (and all its tasks) from a dictionary."""
        pet = cls(
            name=data["name"],
            species=data["species"],
            age_years=data.get("age_years", 0),
        )
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet

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

    # --- Persistence ---

    def to_dict(self) -> dict:
        """Serialize the entire owner graph to a plain dictionary."""
        return {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "preferences": self.preferences,
            "pets": [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Owner":
        """Reconstruct an Owner (plus all pets and tasks) from a dictionary."""
        owner = cls(
            name=data["name"],
            available_minutes=data.get("available_minutes", 120),
            preferences=data.get("preferences", []),
        )
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def save_to_json(self, filepath: str = "data.json") -> None:
        """Write the owner's full state to a JSON file."""
        Path(filepath).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load_from_json(cls, filepath: str = "data.json") -> "Owner":
        """Load an Owner from a JSON file. Raises FileNotFoundError if missing."""
        data = json.loads(Path(filepath).read_text())
        return cls.from_dict(data)

    def __str__(self) -> str:
        pet_names = ", ".join(p.name for p in self.pets) if self.pets else "no pets yet"
        return f"{self.name} ({self.available_minutes} min available | pets: {pet_names})"


# ===========================================================================
# ScheduledTask
# ===========================================================================

@dataclass
class ScheduledTask:
    """One task placed at a concrete time slot in the day."""

    task: Task
    pet_name: str
    start_minute: int
    reason: str

    @property
    def end_minute(self) -> int:
        """Minute when this task finishes."""
        return self.start_minute + self.task.duration_minutes

    def time_label(self, day_start_hour: int = 8) -> str:
        """Format as a readable range like '08:00 – 08:20'."""
        def fmt(offset: int) -> str:
            h = day_start_hour + offset // 60
            m = offset % 60
            return f"{h:02d}:{m:02d}"
        return f"{fmt(self.start_minute)} – {fmt(self.end_minute)}"


# ===========================================================================
# Scheduler
# ===========================================================================

class Scheduler:
    """
    The brain of PawPal+.

    Provides two scheduling strategies, plus sorting, filtering,
    recurring task renewal, and conflict detection.
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
        """Sort tasks by duration, shortest first by default."""
        return sorted(tasks, key=lambda t: t.duration_minutes, reverse=not ascending)

    def sort_by_due_date(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by due date earliest first; tasks without a date go last."""
        return sorted(tasks, key=lambda t: t.due_date or date.max)

    def filter_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Return pending tasks sorted high → medium → low."""
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
        """Filter a task list by pet name, completion status, or category."""
        result = list(tasks)
        if pet_name is not None:
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
        """Mark a task done and queue the next occurrence if it recurs."""
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
        Scan for overlapping time slots using the classic interval test.
        Returns plain-English warning strings; empty list means no conflicts.
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
    # Challenge 1 — Weighted scheduling
    #
    # The standard scheduler ranks purely by priority tier.  The weighted
    # scheduler combines three signals into a single numeric score:
    #
    #   priority_score  — HIGH=30, MEDIUM=20, LOW=10
    #   urgency_score   — bonus if the task is overdue or due very soon
    #   category_score  — configurable per-category weight (medication > feeding > walk …)
    #
    # This means an overdue medium-priority medication can outrank a
    # high-priority low-urgency walk, which is closer to how a real pet
    # owner would actually make the call.
    # ------------------------------------------------------------------

    def score_task(
        self,
        task: Task,
        category_weights: Optional[Dict[str, int]] = None,
    ) -> int:
        """
        Compute a composite urgency score for a task.

        Higher score = should be scheduled sooner.
        """
        weights = category_weights or _DEFAULT_CATEGORY_WEIGHTS

        priority_score = _PRIORITY_SCORE[task.priority]

        urgency_score = 0
        if task.due_date:
            days_until = (task.due_date - date.today()).days
            if days_until <= 0:
                urgency_score = 15   # overdue — bump it to the front
            elif days_until == 1:
                urgency_score = 8    # due tomorrow
            elif days_until <= 3:
                urgency_score = 3    # due very soon

        category_score = weights.get(task.category, 1)

        return priority_score + urgency_score + category_score

    def weighted_schedule(
        self,
        category_weights: Optional[Dict[str, int]] = None,
    ) -> List[ScheduledTask]:
        """
        Build a schedule using composite scores instead of pure priority tiers.

        Tasks are scored on priority, due-date urgency, and category importance,
        then packed greedily into the time budget highest-score first.
        """
        pending = [t for t in self.tasks if not t.is_completed]
        scored = sorted(
            pending,
            key=lambda t: self.score_task(t, category_weights),
            reverse=True,
        )

        schedule: List[ScheduledTask] = []
        time_used = 0
        budget = self.owner.available_minutes

        for task in scored:
            if time_used + task.duration_minutes <= budget:
                pet_name = self._find_pet_name(task)
                score = self.score_task(task, category_weights)
                reason = self._build_weighted_reason(task, score, time_used, budget)
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

    # ------------------------------------------------------------------
    # Schedule generation (standard)
    # ------------------------------------------------------------------

    def generate_schedule(self) -> List[ScheduledTask]:
        """
        Build the day's plan using pure priority ordering.

        Walks tasks high→medium→low and slots each one in if it fits
        the remaining time budget.
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
        """Return a plain-English summary of the schedule and skipped tasks."""
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
        """Look up which pet owns this task, falling back to 'unknown'."""
        if self.pet:
            return self.pet.name
        for pet in self.owner.pets:
            if task in pet.tasks:
                return pet.name
        return "unknown"

    def _build_reason(self, task: Task, time_used: int, budget: int) -> str:
        """One-sentence reason for the standard scheduler."""
        remaining = budget - time_used
        note = {
            Priority.HIGH:   "High priority — goes in first",
            Priority.MEDIUM: "Medium priority — fits the available window",
            Priority.LOW:    "Low priority — there's room, so why not",
        }[task.priority]
        return f"{note}. ({task.duration_minutes} min needed, {remaining} min left)"

    def _build_weighted_reason(self, task: Task, score: int, time_used: int, budget: int) -> str:
        """One-sentence reason for the weighted scheduler, showing the composite score."""
        remaining = budget - time_used
        urgency = ""
        if task.due_date:
            days = (task.due_date - date.today()).days
            if days <= 0:
                urgency = ", overdue"
            elif days == 1:
                urgency = ", due tomorrow"
            elif days <= 3:
                urgency = ", due soon"
        return (
            f"Weighted score {score} "
            f"({task.priority.value} priority, {task.category}{urgency}). "
            f"({task.duration_minutes} min needed, {remaining} min left)"
        )
