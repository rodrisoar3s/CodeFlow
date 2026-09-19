import os
import webview
from backend.api import Api
from backend.db import init_db, get_conn
from backend.scheduler import start_scheduler
from backend.tray import start_tray
from backend.notifier import set_custom_sound

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "ui", "assets", "icon.ico")


def load_saved_sounds():
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM settings WHERE key LIKE 'sound_%'").fetchall()
    conn.close()
    for row in rows:
        kind = row["key"].replace("sound_", "")
        if row["value"]:
            set_custom_sound(kind, row["value"])


def on_closing(window):
    # Instead of closing the app, hide the window and keep running in the tray
    window.hide()
    return False  # False = cancel the actual window close


if __name__ == "__main__":
    init_db()
    load_saved_sounds()
    api = Api()

    window = webview.create_window(
        title="CodeFlow",
        url="ui/index.html",
        js_api=api,
        width=1280,
        height=800,
        min_size=(1000, 650),
        background_color="#1e1e1e",
    )

    window.events.closing += on_closing

    start_scheduler()

    def after_start():
        start_tray(ICON_PATH, window)

    webview.start(after_start, debug=True, icon=ICON_PATH)
