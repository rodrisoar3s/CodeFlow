import os
import sys
import socket
import ctypes
import webview
from backend.api import Api
from backend.db import init_db, get_conn
from backend.scheduler import start_scheduler
from backend.tray import start_tray
from backend.notifier import set_custom_sound

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Fixed local port used only as a single-instance lock (no data is sent through it)
SINGLE_INSTANCE_PORT = 51837


def resource_path(relative):
    """Resolves a path both when running from source and when packaged as a .exe."""
    if getattr(sys, "_MEIPASS", None):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(BASE_DIR, relative)


ICON_PATH = resource_path(os.path.join("ui", "assets", "icon.ico"))
INDEX_PATH = resource_path(os.path.join("ui", "index.html"))


def acquire_single_instance_lock():
    """Returns the bound socket if this is the only instance, or None if another is already running."""
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_socket.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        return lock_socket
    except OSError:
        return None


def show_already_running_message():
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(
            0, "CodeFlow is already running.", "CodeFlow", 0x40  # MB_ICONINFORMATION
        )
    else:
        print("CodeFlow is already running.")


def load_saved_sounds():
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM settings WHERE key LIKE 'sound_%'").fetchall()
    conn.close()
    for row in rows:
        kind = row["key"].replace("sound_", "")
        if row["value"]:
            set_custom_sound(kind, row["value"])


def on_closing(window):
    # Clicking X hides the window and keeps running in the system tray.
    # Fully quitting only happens via the tray icon's "Quit" option.
    window.hide()
    return False  # False = cancel the actual window close


if __name__ == "__main__":
    lock = acquire_single_instance_lock()
    if lock is None:
        show_already_running_message()
        sys.exit(0)

    init_db()
    load_saved_sounds()
    api = Api()

    window = webview.create_window(
        title="CodeFlow",
        url=INDEX_PATH,
        js_api=api,
        width=1280,
        height=800,
        min_size=(1000, 650),
        background_color="#1e1e1e",
    )

    window.events.closing += on_closing

    def after_start():
        start_tray(ICON_PATH, window)

    start_scheduler()

    is_packaged = getattr(sys, "frozen", False)
    webview.start(after_start, debug=not is_packaged, icon=ICON_PATH)
