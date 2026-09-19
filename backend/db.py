import os
import sys
import sqlite3
from pathlib import Path

if getattr(sys, "frozen", False):
    # Running as a packaged .exe: store user data in a persistent, writable
    # location instead of PyInstaller's temporary extraction folder,
    # which gets deleted every time the app closes.
    DB_PATH = Path(os.getenv("APPDATA", str(Path.home()))) / "CodeFlow" / "manager.db"
else:
    DB_PATH = Path(__file__).parent.parent / "data" / "manager.db"

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            folder_path TEXT,
            value_eur REAL DEFAULT 0,
            status TEXT DEFAULT 'active',   -- active | delivered | paid
            description TEXT DEFAULT '',
            due_date TEXT,
            warn_hours_before INTEGER DEFAULT 48,
            notified INTEGER DEFAULT 0,
            pinned INTEGER DEFAULT 0,
            last_opened TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'todo',   -- todo | progress | blocked | done
            priority TEXT DEFAULT 'media', -- alta | media | baixa (high | medium | low)
            notes TEXT DEFAULT '',
            due_date TEXT,
            warn_hours_before INTEGER DEFAULT 24,
            notified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS subtasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()

    # Migration: add new columns to databases created by older versions
    existing_cols = [r["name"] for r in conn.execute("PRAGMA table_info(projects)")]
    if "status" not in existing_cols:
        conn.execute("ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'active'")
    if "pinned" not in existing_cols:
        conn.execute("ALTER TABLE projects ADD COLUMN pinned INTEGER DEFAULT 0")
    if "last_opened" not in existing_cols:
        conn.execute("ALTER TABLE projects ADD COLUMN last_opened TEXT")
    if "description" not in existing_cols:
        conn.execute("ALTER TABLE projects ADD COLUMN description TEXT DEFAULT ''")
    if "due_date" not in existing_cols:
        conn.execute("ALTER TABLE projects ADD COLUMN due_date TEXT")
    if "warn_hours_before" not in existing_cols:
        conn.execute("ALTER TABLE projects ADD COLUMN warn_hours_before INTEGER DEFAULT 48")
    if "notified" not in existing_cols:
        conn.execute("ALTER TABLE projects ADD COLUMN notified INTEGER DEFAULT 0")

    # Semantic migration: old binary 'done' status now means 'paid'
    conn.execute("UPDATE projects SET status = 'paid' WHERE status = 'done'")

    existing_task_cols = [r["name"] for r in conn.execute("PRAGMA table_info(tasks)")]
    if "notified" not in existing_task_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN notified INTEGER DEFAULT 0")
    if "priority" not in existing_task_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN priority TEXT DEFAULT 'media'")
    if "notes" not in existing_task_cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN notes TEXT DEFAULT ''")

    conn.commit()
    conn.close()
