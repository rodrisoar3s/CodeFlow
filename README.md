

# CodeFlow

<img width="529" height="472" alt="icon" src="https://github.com/user-attachments/assets/60a96990-bfd1-43cd-a72c-d9fd9ab082c1" />


A desktop project manager for developers — calendar, kanban tasks, deadline notifications, and a built-in file explorer with one-click "Open in VSCode". Built with Python + [pywebview](https://pywebview.flowrl.com/).


<img width="480" height="270" alt="CodeFlow_logo_animation_20260920004234" src="https://github.com/user-attachments/assets/e447c5a2-2494-47ac-936b-9ce0b3b481bb"/>



## Features

- **Home** — weekly deadline overview, total earnings from paid projects
- **Projects** — kanban board per project (To do / In progress / Blocked / Done), priorities, subtasks, notes
- **Calendar** — monthly view with task titles shown directly on each day
- **File Explorer** — browse and edit project files without leaving the app
- **Open in VSCode** — one click, using the `code` CLI
- **Deadline tracking** — separate delivery dates for tasks and for the whole project (Active → Delivered → Paid)
- **Native notifications** — colored toast popups (warning / expired / success) with configurable `.wav` sounds, works even when the window is closed (runs from the system tray)
- **Settings** — language (English / Português), light/dark theme, per-notification sound

## Requirements

- Python 3.10+
- Windows (the VSCode integration, tray icon, and sound playback are Windows-specific; other platforms may need adjustments)
- [VS Code](https://code.visualstudio.com/) with the `code` command available in your PATH (optional, only needed for the "Open in VSCode" button)

## Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r requirements.txt
python main.py
```

## Project structure

```
main.py                 # entry point — window, tray, scheduler
backend/
  api.py                # JS <-> Python bridge (all app logic)
  db.py                 # SQLite schema + migrations
  scheduler.py           # background thread checking deadlines
  notifier.py            # colored toast notifications
  tray.py                # system tray icon
  i18n.py                 # backend notification translations
ui/
  index.html             # entire frontend (single-page app, vanilla JS)
  assets/
    icon.ico
    sounds/               # put your own .wav files here (aviso.wav, expirado.wav, sucesso.wav)
data/
  manager.db              # created automatically on first run (gitignored)
```

## Notification sounds

Drop `.wav` files into `assets/sounds/` — or pick them from the Settings page inside the app. If no custom sound is set, a default Windows beep plays instead.

## Contributing

This is a personal tool shared as-is. Feel free to fork, open issues, or send pull requests — no formal process, just be reasonable.

## License

MIT — see [LICENSE](LICENSE).
