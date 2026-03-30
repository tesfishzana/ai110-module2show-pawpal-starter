import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Pet care planning assistant — build a daily schedule for your pet.")

# ---------------------------------------------------------------------------
# Step 2 — Application "memory"
#
# Streamlit re-runs this entire file from top to bottom on every interaction.
# Storing the Owner object in st.session_state means it survives those reruns;
# we only create it once (the very first load), then reuse the same instance.
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=120)

owner: Owner = st.session_state.owner  # convenient alias; same object, not a copy

# ---------------------------------------------------------------------------
# Section 1 — Owner settings
# ---------------------------------------------------------------------------

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
        # Update the persisted Owner object directly — no recreation needed.
        owner.name = new_name
        owner.set_available_time(int(new_time))
        st.success(f"Saved! {owner.name} has {owner.available_minutes} min today.")

# ---------------------------------------------------------------------------
# Section 2 — Pet management
# ---------------------------------------------------------------------------

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
            # Step 3 — wire UI action to the actual class method
            new_pet = Pet(name=pet_name.strip(), species=species, age_years=int(pet_age))
            owner.add_pet(new_pet)
            st.rerun()

if owner.pets:
    for pet in owner.pets:
        st.markdown(f"**{pet.name}** — {pet.species}, age {pet.age_years}  ({len(pet.tasks)} task(s))")
else:
    st.info("No pets yet. Add one above.")

# ---------------------------------------------------------------------------
# Section 3 — Task management
# ---------------------------------------------------------------------------

st.header("3. Care Tasks")

if not owner.pets:
    st.warning("Add a pet first before adding tasks.")
else:
    # Let the user pick which pet gets the new task
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
            # Step 3 — call pet.add_task() instead of appending to a dict list
            new_task = Task(
                description=task_desc.strip(),
                category=category,
                duration_minutes=int(duration),
                priority=Priority(priority),
                frequency=frequency,
            )
            selected_pet.add_task(new_task)
            st.rerun()

    # Show all pets and their tasks so the owner can see the full picture
    st.subheader("All tasks by pet")
    any_tasks = False
    for pet in owner.pets:
        if pet.tasks:
            any_tasks = True
            st.markdown(f"**{pet.name}**")
            rows = [
                {
                    "Description": t.description,
                    "Category": t.category,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority.value,
                    "Frequency": t.frequency,
                    "Done": "yes" if t.is_completed else "no",
                }
                for t in pet.tasks
            ]
            st.table(rows)

    if not any_tasks:
        st.info("No tasks yet. Add one above.")

    # Quick "clear all tasks" escape hatch for when you want to start over
    if any_tasks and st.button("Clear all tasks for all pets"):
        for pet in owner.pets:
            pet.tasks.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# Section 4 — Generate the schedule
# ---------------------------------------------------------------------------

st.divider()
st.header("4. Generate Today's Schedule")

if st.button("Generate schedule", type="primary"):
    all_tasks = owner.get_all_tasks()
    if not all_tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        # Scheduler pulls tasks from owner.pets automatically — no manual conversion
        scheduler = Scheduler(owner=owner)
        schedule = scheduler.generate_schedule()

        if not schedule:
            st.error(
                "No tasks fit within the available time. "
                "Try increasing available time or shortening task durations."
            )
        else:
            st.success(
                f"Scheduled {len(schedule)} of {len(all_tasks)} task(s) "
                f"across {len(owner.pets)} pet(s) for {owner.name}."
            )

            rows = [
                {
                    "Time": entry.time_label(),
                    "Pet": entry.pet_name,
                    "Task": entry.task.description,
                    "Category": entry.task.category,
                    "Duration (min)": entry.task.duration_minutes,
                    "Priority": entry.task.priority.value,
                    "Reason": entry.reason,
                }
                for entry in schedule
            ]
            st.table(rows)

            skipped_descs = {e.task.description for e in schedule}
            skipped = [t for t in all_tasks if t.description not in skipped_descs]
            if skipped:
                st.warning(f"{len(skipped)} task(s) didn't fit in the time budget:")
                for t in skipped:
                    st.write(
                        f"- **{t.description}** — {t.duration_minutes} min "
                        f"({t.priority.value} priority)"
                    )

            with st.expander("Full plan explanation"):
                st.text(scheduler.explain_plan(schedule))
