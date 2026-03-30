import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Pet care planning assistant — build a daily schedule for your pet.")

# ===========================================================================
# Challenge 3 & 4 — Emoji helpers for colour-coded display
# ===========================================================================

_PRIORITY_EMOJI = {
    "high":   "🔴 High",
    "medium": "🟡 Medium",
    "low":    "🟢 Low",
}

_CATEGORY_EMOJI = {
    "walk":       "🦮 walk",
    "feeding":    "🍽️ feeding",
    "medication": "💊 medication",
    "grooming":   "✂️ grooming",
    "enrichment": "🎾 enrichment",
    "other":      "📋 other",
}


def fmt_priority(p: str) -> str:
    return _PRIORITY_EMOJI.get(p, p)


def fmt_category(c: str) -> str:
    return _CATEGORY_EMOJI.get(c, c)


def fmt_status(is_done: bool) -> str:
    return "✅ done" if is_done else "⏳ pending"


# ===========================================================================
# Challenge 2 — Persistence helpers
#
# On first load we try to restore the owner from data.json.
# Every mutation that changes meaningful state calls save_owner() so the file
# stays in sync without the user needing to click a "Save" button.
# ===========================================================================

DATA_FILE = "data.json"


def load_owner() -> Owner:
    """Try to load from data.json; return a fresh default owner if it doesn't exist."""
    try:
        return Owner.load_from_json(DATA_FILE)
    except (FileNotFoundError, KeyError, ValueError):
        return Owner(name="Jordan", available_minutes=120)


def save_owner(owner: Owner) -> None:
    """Write the current owner state to data.json silently."""
    try:
        owner.save_to_json(DATA_FILE)
    except OSError:
        pass  # don't crash the app if the filesystem isn't writable


# ===========================================================================
# Session state bootstrap
# ===========================================================================

if "owner" not in st.session_state:
    st.session_state.owner = load_owner()

owner: Owner = st.session_state.owner

# ===========================================================================
# Section 1 — Owner settings
# ===========================================================================

st.header("1. Owner Settings")

with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("Your name", value=owner.name)
    with col2:
        new_time = st.number_input(
            "Available time today (minutes)",
            min_value=15, max_value=480, value=owner.available_minutes, step=15,
        )
    if st.form_submit_button("Save owner settings"):
        owner.name = new_name
        owner.set_available_time(int(new_time))
        save_owner(owner)
        st.success(f"Saved — {owner.name} has {owner.available_minutes} min today.")

# ===========================================================================
# Section 2 — Pet management
# ===========================================================================

st.header("2. Your Pets")

with st.form("add_pet_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        pet_name = st.text_input("Pet name", value="Mochi")
    with col2:
        species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
    with col3:
        pet_age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)

    if st.form_submit_button("Add pet"):
        if pet_name.strip():
            owner.add_pet(Pet(name=pet_name.strip(), species=species, age_years=int(pet_age)))
            save_owner(owner)
            st.rerun()

if owner.pets:
    for pet in owner.pets:
        pending = len(pet.pending_tasks())
        done = len(pet.tasks) - pending
        st.markdown(
            f"**{pet.name}** — {pet.species}, age {pet.age_years} &nbsp;|&nbsp; "
            f"{pending} pending, {done} done"
        )
else:
    st.info("No pets yet. Add one above.")

# ===========================================================================
# Section 3 — Task management
# ===========================================================================

st.header("3. Care Tasks")

if not owner.pets:
    st.warning("Add a pet before adding tasks.")
else:
    pet_names = [p.name for p in owner.pets]
    selected_name = st.selectbox("Add task to:", pet_names)
    selected_pet: Pet = next(p for p in owner.pets if p.name == selected_name)

    with st.form("add_task_form", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
        with c1:
            task_desc = st.text_input("Task description", value="Morning walk")
        with c2:
            category = st.selectbox(
                "Category",
                ["walk", "feeding", "medication", "grooming", "enrichment", "other"],
            )
        with c3:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with c4:
            priority = st.selectbox("Priority", ["high", "medium", "low"])
        with c5:
            frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])

        if st.form_submit_button("Add task") and task_desc.strip():
            selected_pet.add_task(Task(
                description=task_desc.strip(),
                category=category,
                duration_minutes=int(duration),
                priority=Priority(priority),
                frequency=frequency,
            ))
            save_owner(owner)
            st.rerun()

    # --- Quick stats ---
    all_tasks = owner.get_all_tasks()
    if all_tasks:
        total = len(all_tasks)
        pending_count = sum(1 for t in all_tasks if not t.is_completed)
        done_count = total - pending_count
        m1, m2, m3 = st.columns(3)
        m1.metric("Total tasks", total)
        m2.metric("⏳ Pending", pending_count)
        m3.metric("✅ Completed", done_count)

    # --- View, sort, and filter tasks ---
    with st.expander("View & sort tasks", expanded=False):
        if not all_tasks:
            st.info("No tasks yet.")
        else:
            scheduler_view = Scheduler(owner=owner)

            col_sort, col_filter = st.columns(2)
            with col_sort:
                sort_by = st.selectbox(
                    "Sort by",
                    ["Priority (default)", "Duration (shortest first)", "Duration (longest first)", "Due date"],
                    key="sort_by",
                )
            with col_filter:
                filter_cat = st.selectbox(
                    "Filter by category",
                    ["All"] + list(_CATEGORY_EMOJI.keys()),
                    key="filter_cat",
                )

            tasks_to_show = list(all_tasks)
            if sort_by == "Duration (shortest first)":
                tasks_to_show = scheduler_view.sort_by_duration(tasks_to_show, ascending=True)
            elif sort_by == "Duration (longest first)":
                tasks_to_show = scheduler_view.sort_by_duration(tasks_to_show, ascending=False)
            elif sort_by == "Due date":
                tasks_to_show = scheduler_view.sort_by_due_date(tasks_to_show)
            else:
                tasks_to_show = scheduler_view.filter_by_priority(tasks_to_show)

            if filter_cat != "All":
                tasks_to_show = scheduler_view.filter_tasks(tasks_to_show, category=filter_cat)

            if not tasks_to_show:
                st.info("No tasks match the selected filter.")
            else:
                rows = [
                    {
                        "Description": t.description,
                        "Pet": scheduler_view._find_pet_name(t),
                        "Category": fmt_category(t.category),
                        "Duration (min)": t.duration_minutes,
                        "Priority": fmt_priority(t.priority.value),
                        "Frequency": t.frequency,
                        "Status": fmt_status(t.is_completed),
                    }
                    for t in tasks_to_show
                ]
                st.table(rows)

    # --- Mark a task complete ---
    with st.expander("Mark a task complete", expanded=False):
        scheduler_view = Scheduler(owner=owner)
        pending_tasks = [t for t in all_tasks if not t.is_completed]
        if not pending_tasks:
            st.info("All tasks are already done!")
        else:
            task_labels = {
                f"{fmt_category(t.category)}  {t.description}  ({scheduler_view._find_pet_name(t)}, {t.frequency})": t
                for t in pending_tasks
            }
            chosen_label = st.selectbox("Choose task to complete:", list(task_labels.keys()))
            chosen_task = task_labels[chosen_label]
            chosen_pet = next(
                (p for p in owner.pets if chosen_task in p.tasks),
                owner.pets[0],
            )

            if st.button("Mark complete"):
                renewal = Scheduler(owner=owner).mark_task_complete(chosen_task, chosen_pet)
                save_owner(owner)
                if renewal:
                    st.success(
                        f"✅ '{chosen_task.description}' marked complete. "
                        f"Next occurrence queued for **{renewal.due_date}**."
                    )
                else:
                    st.success(f"✅ '{chosen_task.description}' marked complete (no renewal for as-needed tasks).")
                st.rerun()

    if all_tasks and st.button("Clear all tasks for all pets"):
        for pet in owner.pets:
            pet.tasks.clear()
        save_owner(owner)
        st.rerun()

# ===========================================================================
# Section 4 — Generate the schedule
# ===========================================================================

st.divider()
st.header("4. Generate Today's Schedule")

# Challenge 1 — let the user pick between standard and weighted scheduling
schedule_mode = st.radio(
    "Scheduling mode",
    ["Standard (priority-first)", "Smart (weighted score)"],
    horizontal=True,
    help=(
        "**Standard** ranks tasks strictly by priority tier (high → medium → low). "
        "**Smart** combines priority, due-date urgency, and category importance into "
        "a single score — so an overdue medication can outrank a non-urgent high-priority walk."
    ),
)

if st.button("Generate schedule", type="primary"):
    all_tasks = owner.get_all_tasks()
    if not all_tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        scheduler = Scheduler(owner=owner)
        if schedule_mode == "Smart (weighted score)":
            schedule = scheduler.weighted_schedule()
            mode_label = "Smart weighted"
        else:
            schedule = scheduler.generate_schedule()
            mode_label = "Standard priority"

        if not schedule:
            st.error(
                "No tasks fit within the available time. "
                "Try increasing available time or shortening task durations."
            )
        else:
            st.success(
                f"**{mode_label}** schedule — "
                f"**{len(schedule)}** of **{len(all_tasks)}** task(s) "
                f"across **{len(owner.pets)}** pet(s) for **{owner.name}**."
            )

            # Conflict detection — shown before the table so it's hard to miss
            conflicts = scheduler.detect_conflicts(schedule)
            if conflicts:
                st.warning(f"**{len(conflicts)} scheduling conflict(s) detected:**")
                for w in conflicts:
                    st.write(w)
            else:
                st.info("✅ No scheduling conflicts detected.")

            # Schedule table with emoji formatting
            rows = [
                {
                    "Time": entry.time_label(),
                    "Pet": entry.pet_name,
                    "Task": entry.task.description,
                    "Category": fmt_category(entry.task.category),
                    "Duration (min)": entry.task.duration_minutes,
                    "Priority": fmt_priority(entry.task.priority.value),
                    "Why scheduled": entry.reason,
                }
                for entry in schedule
            ]
            st.table(rows)

            # Skipped tasks
            skipped_ids = {id(e.task) for e in schedule}
            skipped = [t for t in all_tasks if id(t) not in skipped_ids and not t.is_completed]
            if skipped:
                st.warning(f"**{len(skipped)} task(s) didn't fit in today's time budget:**")
                for t in skipped:
                    st.write(
                        f"- {fmt_priority(t.priority.value)}  **{t.description}** "
                        f"— {t.duration_minutes} min"
                    )

            with st.expander("Full plan explanation"):
                st.text(scheduler.explain_plan(schedule))
