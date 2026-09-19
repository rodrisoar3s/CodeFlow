import os
import threading
import webview
from backend.i18n import tr

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(BASE_DIR, "..", "assets", "sounds")

# Notification type -> color + default sound (label comes from i18n)
STYLES = {
    "aviso": {"color": "#d7ba7d", "bg": "#2d2a1e", "label_key": "label_aviso", "sound": "aviso.wav"},
    "expirado": {"color": "#f14c4c", "bg": "#2d1e1e", "label_key": "label_expirado", "sound": "expirado.wav"},
    "sucesso": {"color": "#4ec9b0", "bg": "#1e2d29", "label_key": "label_sucesso", "sound": "sucesso.wav"},
}

# User-chosen sound path per type (filled in by the Settings page)
_custom_sounds = {"aviso": None, "expirado": None, "sucesso": None}


def set_custom_sound(kind, filepath):
    if kind in _custom_sounds:
        _custom_sounds[kind] = filepath


def _play_sound(kind):
    if not HAS_WINSOUND:
        return
    path = _custom_sounds.get(kind) or os.path.join(SOUNDS_DIR, STYLES[kind]["sound"])
    if os.path.isfile(path):
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    else:
        winsound.MessageBeep()


def _toast_html(kind, title, message):
    s = STYLES[kind]
    return f"""
    <html><head><style>
        body {{
            margin:0; padding:0; background:{s['bg']};
            border-left:4px solid {s['color']};
            font-family: -apple-system, 'Segoe UI', sans-serif;
            color:#d4d4d4; overflow:hidden;
        }}
        .wrap {{ padding:14px 16px; }}
        .label {{
            font-size:10px; letter-spacing:.5px; color:{s['color']};
            font-family:'JetBrains Mono', monospace; margin-bottom:6px;
        }}
        .title {{ font-size:13px; font-weight:600; color:#fff; margin-bottom:4px; }}
        .msg {{ font-size:12px; color:#aaa; }}
    </style></head>
    <body>
        <div class="wrap">
            <div class="label">{tr(s['label_key'])}</div>
            <div class="title">{title}</div>
            <div class="msg">{message}</div>
        </div>
    </body></html>
    """


def show_toast(kind, title, message, duration=6):
    """Shows a custom colored toast notification and plays the configured sound."""
    if kind not in STYLES:
        kind = "aviso"

    _play_sound(kind)

    screen = webview.screens[0] if webview.screens else None
    width, height = 340, 90
    if screen:
        x = screen.width - width - 24
        y = screen.height - height - 60
    else:
        x, y = 100, 100

    toast = webview.create_window(
        title="",
        html=_toast_html(kind, title, message),
        width=width,
        height=height,
        x=x,
        y=y,
        frameless=True,
        easy_drag=False,
        on_top=True,
        background_color="#1e1e1e",
    )

    def auto_close():
        try:
            toast.destroy()
        except Exception:
            pass

    threading.Timer(duration, auto_close).start()
    return toast
