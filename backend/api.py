import subprocess
import shutil
import os
import webview
from backend.db import get_conn
from backend.notifier import show_toast
from backend.i18n import tr


class Api:
    # ---------- Projects ----------
    def get_projects(self):
        conn = get_conn()
        rows = conn.execute("""
            SELECT p.*,
                (SELECT COUNT(*) FROM tasks WHERE project_id = p.id AND status != 'done') AS open_tasks
            FROM projects p
            ORDER BY p.pinned DESC, p.last_opened IS NULL, p.last_opened DESC, p.created_at DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def toggle_pin(self, project_id, pinned):
        conn = get_conn()
        conn.execute("UPDATE projects SET pinned = ? WHERE id = ?", (1 if pinned else 0, project_id))
        conn.commit()
        conn.close()
        return {"ok": True}

    def touch_project(self, project_id):
        conn = get_conn()
        conn.execute(
            "UPDATE projects SET last_opened = datetime('now') WHERE id = ?", (project_id,)
        )
        conn.commit()
        conn.close()
        return {"ok": True}

    def add_project(self, name, folder_path="", value_eur=0, description="", due_date=None, warn_hours_before=48):
        value_eur = max(0, value_eur or 0)  # never negative
        conn = get_conn()
        conn.execute(
            "INSERT INTO projects (name, folder_path, value_eur, description, due_date, warn_hours_before) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (name, folder_path, value_eur, description, due_date, warn_hours_before),
        )
        conn.commit()
        conn.close()
        return {"ok": True}

    def edit_project(self, project_id, name, folder_path, value_eur, description, due_date, warn_hours_before):
        value_eur = max(0, value_eur or 0)
        conn = get_conn()
        conn.execute(
            "UPDATE projects SET name=?, folder_path=?, value_eur=?, description=?, due_date=?, "
            "warn_hours_before=?, notified=0 WHERE id=?",
            (name, folder_path, value_eur, description, due_date, warn_hours_before, project_id),
        )
        conn.commit()
        conn.close()
        return {"ok": True}

    def delete_project(self, project_id):
        conn = get_conn()
        conn.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()
        return {"ok": True}

    def set_project_status(self, project_id, status):
        conn = get_conn()
        conn.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))
        conn.commit()
        conn.close()
        return {"ok": True}

    def get_project(self, project_id):
        conn = get_conn()
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_week_summary(self):
        """Tasks + project deadlines due within the next 7 days."""
        conn = get_conn()
        items = []

        for r in conn.execute("""
            SELECT tasks.title, tasks.due_date, tasks.status, projects.name AS project_name
            FROM tasks JOIN projects ON projects.id = tasks.project_id
            WHERE tasks.due_date IS NOT NULL AND tasks.status != 'done'
            ORDER BY tasks.due_date ASC
        """).fetchall():
            items.append({"title": r["title"], "due_date": r["due_date"],
                          "project_name": r["project_name"], "kind": "task"})

        for r in conn.execute("""
            SELECT name, due_date FROM projects
            WHERE due_date IS NOT NULL AND status != 'paid'
            ORDER BY due_date ASC
        """).fetchall():
            items.append({"title": "Final delivery", "due_date": r["due_date"],
                          "project_name": r["name"], "kind": "project"})

        conn.close()
        return items

    def set_project_folder(self, project_id, folder_path):
        conn = get_conn()
        conn.execute("UPDATE projects SET folder_path = ? WHERE id = ?", (folder_path, project_id))
        conn.commit()
        conn.close()
        return {"ok": True}

    def pick_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        if result:
            return result[0]
        return None

    def pick_file(self, file_types=None):
        types = tuple(file_types) if file_types else ("Audio Files (*.wav)",)
        try:
            result = webview.windows[0].create_file_dialog(webview.OPEN_DIALOG, file_types=types)
        except Exception as e:
            print(f"[pick_file] error: {e}")
            return None
        if result:
            return result[0]
        return None

    # ---------- Settings ----------
    def get_settings(self):
        conn = get_conn()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        conn.close()
        return {r["key"]: r["value"] for r in rows}

    def set_setting(self, key, value):
        conn = get_conn()
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()
        conn.close()

        if key.startswith("sound_"):
            from backend.notifier import set_custom_sound
            set_custom_sound(key.replace("sound_", ""), value)

        return {"ok": True}

    def test_notification(self, kind):
        show_toast(kind, "CodeFlow", tr("test_message"))
        return {"ok": True}

    # ---------- Tasks ----------
    def get_tasks(self, project_id):
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY due_date IS NULL, due_date ASC",
            (project_id,),
        ).fetchall()
        tasks = []
        for r in rows:
            t = dict(r)
            sub = conn.execute(
                "SELECT COUNT(*) AS total, SUM(done) AS done FROM subtasks WHERE task_id = ?",
                (t["id"],),
            ).fetchone()
            t["subtasks_total"] = sub["total"] or 0
            t["subtasks_done"] = sub["done"] or 0
            tasks.append(t)
        conn.close()
        return tasks

    def get_all_tasks(self):
        conn = get_conn()
        rows = conn.execute("""
            SELECT tasks.*, projects.name AS project_name
            FROM tasks
            JOIN projects ON projects.id = tasks.project_id
            WHERE tasks.due_date IS NOT NULL
            ORDER BY tasks.due_date ASC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_task(self, project_id, title, due_date=None, warn_hours_before=24, priority="media"):
        conn = get_conn()
        conn.execute(
            "INSERT INTO tasks (project_id, title, due_date, warn_hours_before, priority) VALUES (?, ?, ?, ?, ?)",
            (project_id, title, due_date, warn_hours_before, priority),
        )
        conn.commit()
        conn.close()
        return {"ok": True}

    def set_task_status(self, task_id, status):
        conn = get_conn()
        task = conn.execute(
            "SELECT tasks.title, projects.name AS project_name "
            "FROM tasks JOIN projects ON projects.id = tasks.project_id "
            "WHERE tasks.id = ?", (task_id,)
        ).fetchone()
        conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
        conn.close()
        if status == "done" and task:
            show_toast("sucesso", task["project_name"], tr("task_success", title=task["title"]))
        return {"ok": True}

    def set_task_priority(self, task_id, priority):
        conn = get_conn()
        conn.execute("UPDATE tasks SET priority = ? WHERE id = ?", (priority, task_id))
        conn.commit()
        conn.close()
        return {"ok": True}

    def set_task_notes(self, task_id, notes):
        conn = get_conn()
        conn.execute("UPDATE tasks SET notes = ? WHERE id = ?", (notes, task_id))
        conn.commit()
        conn.close()
        return {"ok": True}

    def get_task(self, task_id):
        conn = get_conn()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def delete_task(self, task_id):
        conn = get_conn()
        conn.execute("DELETE FROM subtasks WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return {"ok": True}

    # ---------- Subtasks ----------
    def get_subtasks(self, task_id):
        conn = get_conn()
        rows = conn.execute("SELECT * FROM subtasks WHERE task_id = ? ORDER BY id", (task_id,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def add_subtask(self, task_id, title):
        conn = get_conn()
        conn.execute("INSERT INTO subtasks (task_id, title) VALUES (?, ?)", (task_id, title))
        conn.commit()
        conn.close()
        return {"ok": True}

    def toggle_subtask(self, subtask_id, done):
        conn = get_conn()
        conn.execute("UPDATE subtasks SET done = ? WHERE id = ?", (1 if done else 0, subtask_id))
        conn.commit()
        conn.close()
        return {"ok": True}

    def delete_subtask(self, subtask_id):
        conn = get_conn()
        conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
        conn.commit()
        conn.close()
        return {"ok": True}

    # ---------- Open in VSCode ----------
    def open_in_vscode(self, folder_path):
        code_bin = shutil.which("code")
        if not code_bin:
            return {"ok": False, "error": "VSCode CLI 'code' not found in PATH."}
        try:
            subprocess.Popen([code_bin, folder_path])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------- Monthly earnings (for Home) ----------
    def get_monthly_earnings(self):
        conn = get_conn()
        rows = conn.execute(
            "SELECT name, value_eur FROM projects"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ---------- File explorer ----------
    TEXT_EXTENSIONS = {
        ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".html",
        ".css", ".scss", ".xml", ".yml", ".yaml", ".c", ".cpp", ".h", ".java",
        ".cs", ".php", ".sql", ".sh", ".bat", ".ini", ".cfg", ".env", ".gitignore",
    }

    def _safe_path(self, root, relative):
        """Ensures the final path never escapes the project folder."""
        root_abs = os.path.abspath(root)
        target = os.path.abspath(os.path.join(root_abs, relative or ""))
        if not target.startswith(root_abs):
            raise ValueError("Path is outside the project folder.")
        return target

    def list_dir(self, root, relative=""):
        try:
            path = self._safe_path(root, relative)
            entries = []
            for name in sorted(os.listdir(path)):
                full = os.path.join(path, name)
                entries.append({
                    "name": name,
                    "is_dir": os.path.isdir(full),
                    "path": os.path.relpath(full, os.path.abspath(root)).replace("\\", "/"),
                })
            entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
            return {"ok": True, "entries": entries}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def read_file(self, root, relative):
        try:
            path = self._safe_path(root, relative)
            ext = os.path.splitext(path)[1].lower()
            if ext not in self.TEXT_EXTENSIONS:
                return {"ok": False, "error": "File type not supported by the editor."}
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {"ok": True, "content": content}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def write_file(self, root, relative, content):
        try:
            path = self._safe_path(root, relative)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------- Mark task as done ----------
    def mark_task_done(self, task_id):
        conn = get_conn()
        task = conn.execute(
            "SELECT tasks.title, projects.name AS project_name "
            "FROM tasks JOIN projects ON projects.id = tasks.project_id "
            "WHERE tasks.id = ?", (task_id,)
        ).fetchone()

        conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()

        if task:
            show_toast(
                "sucesso",
                task["project_name"],
                tr("task_success", title=task["title"]),
            )
        return {"ok": True}

    # ---------- Configure custom sound per type ----------
    def set_notification_sound(self, kind, filepath):
        from backend.notifier import set_custom_sound
        set_custom_sound(kind, filepath)
        return {"ok": True}
