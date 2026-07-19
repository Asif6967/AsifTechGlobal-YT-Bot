"""
AsifTechGlobal — Background Tray Server
VS Code band karo, mobile pe kaam karta rahega!

Run: pythonw tray_app.py   (no console window)
  OR: python tray_app.py   (with console)
"""

import os
import sys
import time
import socket
import threading
import webbrowser
import subprocess
import winreg
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

# Tell web_panel where templates and data are
os.environ["ATG_BUNDLE_DIR"] = str(BASE_DIR)
os.environ["ATG_APP_DIR"]    = str(BASE_DIR)

# ── Imports ───────────────────────────────────────────────────────────────────
from web_panel import app as flask_app, init_db, USER_DATA
import pystray
from PIL import Image, ImageDraw, ImageFont

# ── Local IP ──────────────────────────────────────────────────────────────────
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())

LOCAL_IP = get_ip()
PC_URL   = "http://localhost:5000"
MOB_URL  = f"http://{LOCAL_IP}:5000"

# ── Registry startup key ──────────────────────────────────────────────────────
REG_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "AsifTechGlobal"
PY_W     = Path(sys.executable).parent / "pythonw.exe"
TRAY_CMD = f'"{PY_W}" "{BASE_DIR / "tray_app.py"}"'


def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.QueryValueEx(key, REG_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False


def set_startup(enable: bool):
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                         winreg.KEY_SET_VALUE)
    if enable:
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, TRAY_CMD)
    else:
        try:
            winreg.DeleteValue(key, REG_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)


# ── Tray icon image ───────────────────────────────────────────────────────────
def make_icon(running=True):
    size   = 64
    img    = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(img)
    bg     = "#161b22"
    accent = "#00ff88" if running else "#f85149"
    # Dark circle
    draw.ellipse([1, 1, size - 2, size - 2], fill=bg, outline=accent, width=3)
    # ⚡ Lightning bolt polygon
    cx = size // 2
    pts = [
        (cx,      10),   # top tip
        (cx - 10, 32),   # left mid
        (cx,      30),   # center notch
        (cx,      54),   # bottom tip
        (cx + 10, 32),   # right mid
        (cx,      34),   # center notch
    ]
    draw.polygon(pts, fill=accent)
    return img


# ── Flask server ──────────────────────────────────────────────────────────────
_server_started = threading.Event()


def _run_flask():
    init_db()
    USER_DATA.mkdir(parents=True, exist_ok=True)
    _server_started.set()
    flask_app.run(
        host="0.0.0.0", port=5000,
        debug=False, threaded=True, use_reloader=False,
    )


flask_thread = threading.Thread(target=_run_flask, daemon=True, name="flask")
flask_thread.start()
_server_started.wait(timeout=8)  # Wait until Flask is up

# ── TTS greeting ──────────────────────────────────────────────────────────────
def speak(text):
    ps = (f"Add-Type -AssemblyName System.Speech;"
          f"$v=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          f"$v.Rate=-2;$v.Volume=100;$v.Speak('{text}');")
    subprocess.Popen(
        ["powershell.exe", "-WindowStyle", "Hidden", "-NonInteractive",
         "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


# ── Tray menu actions ─────────────────────────────────────────────────────────
def action_open_browser(icon, item):
    webbrowser.open(PC_URL)


def action_copy_mobile(icon, item):
    """Copy mobile URL to clipboard"""
    subprocess.run(
        ["powershell", "-Command", f"Set-Clipboard '{MOB_URL}'"],
        capture_output=True,
    )
    icon.notify(f"Copied!\n{MOB_URL}", "AsifTechGlobal")


def action_toggle_startup(icon, item):
    current = is_startup_enabled()
    set_startup(not current)
    status = "enabled ✓" if not current else "disabled ✗"
    icon.notify(f"Auto-start {status}", "AsifTechGlobal")
    # Rebuild menu to update checkmark
    icon.menu = build_menu(icon)


def action_exit(icon, item):
    icon.notify("AsifTechGlobal server stopped.", "AsifTechGlobal")
    time.sleep(0.8)
    icon.stop()
    os._exit(0)


def build_menu(icon=None):
    startup_on = is_startup_enabled()
    return pystray.Menu(
        pystray.MenuItem("⚡ AsifTechGlobal Bot Server",
                         lambda i, it: None, enabled=False),
        pystray.MenuItem("● Server running on port 5000",
                         lambda i, it: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🌐  Open in Browser (PC)",
                         action_open_browser),
        pystray.MenuItem(f"📱  Mobile URL: {MOB_URL}",
                         action_copy_mobile),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            f"{'✅' if startup_on else '⬜'}  Start with Windows",
            action_toggle_startup,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("❌  Exit / Stop Server",
                         action_exit),
    )


# ── Double-click on tray icon ─────────────────────────────────────────────────
def on_double_click(icon):
    webbrowser.open(PC_URL)


# ── Main ──────────────────────────────────────────────────────────────────────
icon_img = make_icon(running=True)
tray = pystray.Icon(
    name="AsifTechGlobal",
    icon=icon_img,
    title=f"⚡ AsifTechGlobal Bot\n{MOB_URL}",
    menu=build_menu(),
)

# Auto-open browser on first start
webbrowser.open(PC_URL)

# Greeting
speak("AsifTechGlobal bot server started in background.")

# Show startup notification
tray.run_detached()
time.sleep(1)
tray.notify(
    f"Server running!\nMobile: {MOB_URL}\nDouble-click to open browser.",
    "⚡ AsifTechGlobal",
)

# Keep main thread alive (Flask runs in daemon thread)
try:
    while True:
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    pass
