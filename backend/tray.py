import os
import threading
import webview
from PIL import Image
import pystray


def start_tray(icon_path, window):
    image = Image.open(icon_path)

    def on_show(icon_obj, item):
        window.show()

    def on_quit(icon_obj, item):
        icon_obj.stop()
        # Hard-exit guarantees the process is fully gone from Task Manager,
        # instead of possibly lingering due to pywebview's own event loop.
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Open CodeFlow", on_show, default=True),
        pystray.MenuItem("Quit", on_quit),
    )

    tray_icon = pystray.Icon("codeflow", image, "CodeFlow", menu)

    # pystray needs its own thread, separate from the pywebview window
    threading.Thread(target=tray_icon.run, daemon=True).start()
    return tray_icon
