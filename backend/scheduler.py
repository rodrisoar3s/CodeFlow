import time
import threading
from datetime import datetime
from backend.db import get_conn
from backend.notifier import show_toast
from backend.i18n import tr

CHECK_INTERVAL_SECONDS = 60


def _check_and_notify():
    conn = get_conn()
    now = datetime.now()

    # ---------- Tasks ----------
    task_rows = conn.execute("""
        SELECT tasks.id, tasks.title, tasks.due_date, tasks.warn_hours_before,
               tasks.notified, projects.name AS project_name
        FROM tasks
        JOIN projects ON projects.id = tasks.project_id
        WHERE tasks.status != 'done'
          AND tasks.due_date IS NOT NULL
    """).fetchall()

    for row in task_rows:
        try:
            due = datetime.fromisoformat(row["due_date"])
        except (TypeError, ValueError):
            continue

        hours_left = (due - now).total_seconds() / 3600
        notified = row["notified"] or 0

        if hours_left <= 0 and notified < 2:
            show_toast("expirado", row["project_name"], tr("task_overdue", title=row["title"]))
            conn.execute("UPDATE tasks SET notified = 2 WHERE id = ?", (row["id"],))
        elif hours_left <= row["warn_hours_before"] and notified < 1:
            show_toast("aviso", row["project_name"], tr("task_warning", title=row["title"], due=due.strftime('%d/%m %H:%M')))
            conn.execute("UPDATE tasks SET notified = 1 WHERE id = ?", (row["id"],))

    # ---------- Project deadlines ----------
    project_rows = conn.execute("""
        SELECT id, name, due_date, warn_hours_before, notified
        FROM projects
        WHERE status != 'paid' AND due_date IS NOT NULL
    """).fetchall()

    for row in project_rows:
        try:
            due = datetime.fromisoformat(row["due_date"])
        except (TypeError, ValueError):
            continue

        hours_left = (due - now).total_seconds() / 3600
        notified = row["notified"] or 0

        if hours_left <= 0 and notified < 2:
            show_toast("expirado", row["name"], tr("project_overdue"))
            conn.execute("UPDATE projects SET notified = 2 WHERE id = ?", (row["id"],))
        elif hours_left <= row["warn_hours_before"] and notified < 1:
            show_toast("aviso", row["name"], tr("project_warning", due=due.strftime('%d/%m %H:%M')))
            conn.execute("UPDATE projects SET notified = 1 WHERE id = ?", (row["id"],))

    conn.commit()
    conn.close()


def start_scheduler():
    def loop():
        while True:
            try:
                _check_and_notify()
            except Exception as e:
                print(f"[scheduler] error: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
