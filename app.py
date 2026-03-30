import streamlit as st

from pawpal_system import Owner, Pet, Priority, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Pet care planning assistant — build a daily schedule for your pet.")

# ---------------------------------------------------------------------------
# Owner & Pet Info
# ---------------------------------------------------------------------------

st.header("Owner & Pet Info")

col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
    available_time = st.number_input(
        "Available time today (minutes)", min_value=15, max_value=480, value=120, step=15
    )
with col2:
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
    pet_age = st.number_input("Pet age (years)", min_value=0, max_value=30, value=2)

# ---------------------------------------------------------------------------
# Task management
# ---------------------------------------------------------------------------

st.header("Tasks")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

with st.form("add_task_form", clear_on_submit=True):
    c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
    with c1:
        task_desc = st.text_input("Task description", value="Morning walk")
    with c2:
        category = st.selectbox(
            "Category", ["walk", "feeding", "medication", "grooming", "enrichment", "other"]
        )
    with c3:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with c4:
        priority = st.selectbox("Priority", ["high", "medium", "low"])
    with c5:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])

    submitted = st.form_submit_button("Add task")
    if submitted and task_desc.strip():
        st.session_state.tasks.append(
            {
                "description": task_desc.strip(),
                "category": category,
                "duration_minutes": int(duration),
                "priority": priority,
                "frequency": frequency,
            }
        )

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
    if st.button("Clear all tasks"):
        st.session_state.tasks = []
        st.rerun()
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# ---------------------------------------------------------------------------
# Schedule generation
# ---------------------------------------------------------------------------

st.header("Generate Schedule")

if st.button("Generate schedule", type="primary"):
    if not st.session_state.tasks:
        st.warning("Add at least one task before generating a schedule.")
    else:
        owner = Owner(name=owner_name, available_minutes=int(available_time))
        pet = Pet(name=pet_name, species=species, age_years=int(pet_age))
        tasks = [
            Task(
                description=t["description"],
                category=t["category"],
                duration_minutes=t["duration_minutes"],
                priority=Priority(t["priority"]),
                frequency=t.get("frequency", "daily"),
            )
            for t in st.session_state.tasks
        ]

        scheduler = Scheduler(owner=owner, pet=pet, tasks=tasks)
        schedule = scheduler.generate_schedule()

        if not schedule:
            st.error(
                "No tasks fit within the available time. "
                "Try increasing available time or reducing task durations."
            )
        else:
            st.success(f"Scheduled {len(schedule)} of {len(tasks)} task(s) for {pet_name}.")

            rows = [
                {
                    "Time": entry.time_label(),
                    "Task": entry.task.description,
                    "Category": entry.task.category,
                    "Duration (min)": entry.task.duration_minutes,
                    "Priority": entry.task.priority.value,
                    "Reason": entry.reason,
                }
                for entry in schedule
            ]
            st.table(rows)

            skipped_titles = {e.task.description for e in schedule}
            skipped = [t for t in tasks if t.description not in skipped_titles]
            if skipped:
                st.warning(f"{len(skipped)} task(s) not scheduled due to time constraint:")
                for t in skipped:
                    st.write(f"- **{t.description}** ({t.duration_minutes} min, {t.priority.value} priority)")

            with st.expander("Full plan explanation"):
                st.text(scheduler.explain_plan(schedule))
