"""
Study Planner - a simple command-line app.

Features:
  - Add study tasks (subject, topic, deadline, estimated hours, priority)
  - Log hours studied / mark tasks complete
  - Auto-generate a daily study schedule (earliest deadline first)
  - Data is saved to study_planner.json
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_FILE = Path("study_planner.json")
MAX_BLOCK = 2.0  # max hours on one task in a single day block
PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High"}


# ---------- Storage ----------
def load_tasks():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except json.JSONDecodeError:
            print("Warning: data file is corrupted, starting fresh.")
    return []


def save_tasks(tasks):
    DATA_FILE.write_text(json.dumps(tasks, indent=2))


def next_id(tasks):
    return max((t["id"] for t in tasks), default=0) + 1


# ---------- Input helpers ----------
def ask_date(prompt):
    while True:
        raw = input(prompt).strip()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            print("  Please use the format YYYY-MM-DD (e.g. 2026-12-15).")


def ask_number(prompt, cast=float, minimum=0, maximum=None):
    while True:
        try:
            value = cast(input(prompt).strip())
            if value < minimum or (maximum is not None and value > maximum):
                raise ValueError
            return value
        except ValueError:
            print("  Invalid number, try again.")


# ---------- Actions ----------
def add_task(tasks):
    print("\n--- Add Task ---")
    subject = input("Subject (e.g. Math): ").strip() or "General"
    topic = input("Topic (e.g. Integrals): ").strip() or "Revision"
    deadline = ask_date("Deadline (YYYY-MM-DD): ")
    hours = ask_number("Estimated hours needed: ", float, minimum=0.5)
    priority = ask_number("Priority (1=Low, 2=Medium, 3=High): ", int, 1, 3)

    tasks.append({
        "id": next_id(tasks),
        "subject": subject,
        "topic": topic,
        "deadline": deadline.isoformat(),
        "hours": hours,
        "done_hours": 0.0,
        "priority": priority,
        "done": False,
    })
    save_tasks(tasks)
    print("Task added!")


def list_tasks(tasks):
    print("\n--- Your Tasks ---")
    if not tasks:
        print("No tasks yet.")
        return
    today = date.today()
    print(f"{'ID':<4}{'Subject':<12}{'Topic':<18}{'Deadline':<12}{'Progress':<12}{'Priority':<9}Status")
    print("-" * 76)
    for t in sorted(tasks, key=lambda x: (x["done"], x["deadline"])):
        deadline = date.fromisoformat(t["deadline"])
        if t["done"]:
            status = "Done"
        elif deadline < today:
            status = "OVERDUE"
        else:
            status = f"{(deadline - today).days}d left"
        progress = f"{t['done_hours']:g}/{t['hours']:g}h"
        print(f"{t['id']:<4}{t['subject'][:11]:<12}{t['topic'][:17]:<18}"
              f"{t['deadline']:<12}{progress:<12}{PRIORITY_NAMES[t['priority']]:<9}{status}")


def find_task(tasks, task_id):
    return next((t for t in tasks if t["id"] == task_id), None)


def log_progress(tasks):
    list_tasks(tasks)
    if not tasks:
        return
    task = find_task(tasks, ask_number("\nTask ID to update: ", int, 1))
    if not task:
        print("No task with that ID.")
        return
    hours = ask_number("Hours studied today: ", float, minimum=0)
    task["done_hours"] += hours
    if task["done_hours"] >= task["hours"]:
        task["done"] = True
        print("Task completed. Great job!")
    else:
        print(f"Logged. {task['hours'] - task['done_hours']:g}h remaining.")
    save_tasks(tasks)


def delete_task(tasks):
    list_tasks(tasks)
    if not tasks:
        return
    task = find_task(tasks, ask_number("\nTask ID to delete: ", int, 1))
    if task:
        tasks.remove(task)
        save_tasks(tasks)
        print("Task deleted.")
    else:
        print("No task with that ID.")


def generate_plan(tasks):
    print("\n--- Generate Study Plan ---")
    daily_hours = ask_number("Hours you can study per day: ", float, minimum=0.5, maximum=16)
    days = ask_number("Plan how many days ahead? ", int, minimum=1, maximum=60)

    active = [t for t in tasks if not t["done"]]
    if not active:
        print("Nothing to plan, all tasks are done!")
        return

    remaining = {t["id"]: t["hours"] - t["done_hours"] for t in active}
    # Earliest deadline first; higher priority breaks ties
    order = sorted(active, key=lambda t: (t["deadline"], -t["priority"]))
    today = date.today()

    for offset in range(days):
        day = today + timedelta(days=offset)
        capacity = daily_hours
        blocks = []
        progress = True
        while capacity > 0 and progress:
            progress = False
            for t in order:
                if capacity <= 0:
                    break
                if remaining[t["id"]] <= 0 or date.fromisoformat(t["deadline"]) < day:
                    continue
                chunk = min(remaining[t["id"]], capacity, MAX_BLOCK)
                remaining[t["id"]] -= chunk
                capacity -= chunk
                blocks.append((t, chunk))
                progress = True

        print(f"\n{day.strftime('%A, %d %b %Y')}")
        if not blocks:
            print("  Free day")
            continue
        # Merge repeated blocks of the same task
        merged = {}
        for t, h in blocks:
            merged[t["id"]] = (t, merged.get(t["id"], (t, 0))[1] + h)
        for t, h in merged.values():
            print(f"  - {t['subject']}: {t['topic']} ({h:g}h)")

    # Warn about tasks that don't fit before their deadline
    short = [(t, remaining[t["id"]]) for t in active if remaining[t["id"]] > 0]
    if short:
        print("\nNot enough time in this plan for:")
        for t, left in short:
            print(f"  ! {t['subject']} - {t['topic']}: {left:g}h unscheduled "
                  f"(deadline {t['deadline']})")


# ---------- Main loop ----------
def main():
    tasks = load_tasks()
    actions = {
        "1": ("Add task", add_task),
        "2": ("View tasks", list_tasks),
        "3": ("Log study progress", log_progress),
        "4": ("Generate study plan", generate_plan),
        "5": ("Delete task", delete_task),
    }
    while True:
        print("\n===== STUDY PLANNER =====")
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print("6. Quit")
        choice = input("Choose: ").strip()
        if choice == "6":
            print("Happy studying!")
            break
        if choice in actions:
            actions[choice][1](tasks)
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
