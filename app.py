"""
AsifTechGlobal — YT Bot Software  v1.0
Entry point when bundled as .exe via PyInstaller

Modes:
  Normal     : Starts web server + opens browser
  --bot-mode : Runs bot (called internally by web_panel)
"""

import os
import sys
import time
import socket
import threading
import subprocess
from pathlib import Path

from browser_utils import open_browser_url

# ─── Windows UTF-8 console fix (prevents UnicodeEncodeError on box-drawing chars) ─
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ─── Detect frozen (PyInstaller .exe) vs dev mode ────────────────────────────
IS_FROZEN   = getattr(sys, "frozen", False)
BUNDLE_DIR  = Path(sys._MEIPASS) if IS_FROZEN else Path(__file__).parent.resolve()

# User data goes to %APPDATA%\AsifTechGlobal when packaged, else project folder
if IS_FROZEN:
    APP_DIR = Path(os.environ.get("APPDATA", os.path.expanduser("~"))) / "AsifTechGlobal"
else:
    APP_DIR = BUNDLE_DIR

APP_DIR.mkdir(parents=True, exist_ok=True)

# ─── BOT MODE (called as subprocess from web_panel) ──────────────────────────
if "--bot-mode" in sys.argv:
    idx = sys.argv.index("--bot-mode")
    data_dir = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else str(APP_DIR)
    os.environ["BOT_DATA_DIR"] = data_dir
    os.chdir(str(BUNDLE_DIR))
    sys.path.insert(0, str(BUNDLE_DIR))
    from bot import start_bot
    start_bot()
    sys.exit(0)

# ─── NORMAL MODE: Web Server ──────────────────────────────────────────────────

# Tell web_panel where to find templates (bundle dir) and store data (app dir)
os.environ["ATG_BUNDLE_DIR"] = str(BUNDLE_DIR)
os.environ["ATG_APP_DIR"]    = str(APP_DIR)

# Change CWD to APP_DIR so relative paths (db, data) go there
os.chdir(str(APP_DIR))
sys.path.insert(0, str(BUNDLE_DIR))

# Copy default config files to AppData on first run
def _copy_defaults():
    for name in ("config.json", "oauth_config.json"):
        src = BUNDLE_DIR / name
        dst = APP_DIR / name
        if src.exists() and not dst.exists():
            import shutil
            shutil.copy2(src, dst)

_copy_defaults()

# ─── Windows Firewall: Mobile access ke liye port 5000 open karo ─────────────
def add_firewall_rule():
    """Port 5000 pe inbound rule add karo taake mobile access kar sake"""
    try:
        rule = "AsifTechGlobal-Bot"
        check = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={rule}"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=5
        )
        if "No rules match" in check.stdout or "--------" not in check.stdout:
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={rule}", "protocol=TCP", "dir=in",
                 "localport=5000", "action=allow"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW, timeout=5
            )
    except Exception:
        pass

add_firewall_rule()

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def speak(text):
    """TTS via PowerShell .NET Speech"""
    t = text.replace("'", "").replace("\\", "")
    ps = (f"Add-Type -AssemblyName System.Speech;"
          f"$v=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          f"$v.Rate=-2;$v.Volume=100;$v.Speak('{t}');")
    subprocess.Popen(
        ["powershell.exe", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", ps],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def run_server():
    from web_panel import app as flask_app, init_db, USER_DATA
    init_db()
    USER_DATA.mkdir(parents=True, exist_ok=True)
    flask_app.run(host="0.0.0.0", port=5000, debug=False,
                  threaded=True, use_reloader=False)


# ─── Startup Banner ──────────────────────────────────────────────────────────

if os.name == "nt":
    os.system("")   # unlock ANSI colors

R = "\033[0m";  B = "\033[1m"
G = "\033[92m"; C = "\033[96m"; Y = "\033[93m"; M = "\033[95m"

ip = get_ip()

banner = f"""
{B}{G}
  ██████╗ ███████╗██╗███████╗████████╗███████╗ ██████╗██╗  ██╗
  ██╔══██╗██╔════╝██║██╔════╝╚══██╔══╝██╔════╝██╔════╝██║  ██║
  ██████╔╝███████╗██║█████╗     ██║   █████╗  ██║     ███████║
  ██╔══██╗╚════██║██║██╔══╝     ██║   ██╔══╝  ██║     ██╔══██║
  ██████╔╝███████║██║██║        ██║   ███████╗╚██████╗██║  ██║
  ╚═════╝ ╚══════╝╚═╝╚═╝        ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝
{R}
{B}{C}  AsifTechGlobal — YouTube Live Bot  v1.0{R}
{Y}  ══════════════════════════════════════════════════{R}
  {G}✓{R} PC Browser  :  {B}http://localhost:5000{R}
  {G}✓{R} Mobile/Phone:  {B}http://{ip}:5000{R}
  {G}✓{R} iPhone/iPad :  {B}http://{ip}:5000{R}
  {G}✓{R} Koi bhi device (same Wi-Fi pe) browser mein{R}
{Y}  ══════════════════════════════════════════════════{R}
  {M}Register karein  →  Login  →  Bot use karein{R}
{Y}  ══════════════════════════════════════════════════{R}
"""

print(banner)

# Voice greeting
speak("Welcome to AsifTechGlobal. Your YouTube Bot software is starting. Please wait.")

def start_server_thread():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return t

# Start server in background thread
print(f"  Starting server", end="", flush=True)
server_thread = start_server_thread()

for _ in range(6):
    time.sleep(0.5)
    print(".", end="", flush=True)

print(f" {G}{B}Ready!{R}\n")

# Auto-open browser
opened = open_browser_url("http://localhost:5000")
if opened:
    print(f"  {G}✓{R} Browser opened automatically.")
else:
    print(f"  {Y}⚠{R} Browser could not be opened automatically. Please open http://localhost:5000 manually.")
print(f"  {C}📱 Mobile URL: http://{ip}:5000{R}")
print(f"  {Y}⚠  Close this window to stop the server.{R}")
print(f"  {Y}   Press Ctrl+C to exit.{R}\n")

# Keep alive + auto-restart server if it crashes
try:
    while True:
        time.sleep(3)
        if not server_thread.is_alive():
            print(f"\n  {Y}⚠  Server band ho gaya! Auto-restart ho raha hai...{R}")
            time.sleep(2)
            server_thread = start_server_thread()
            print(f"  {G}✓  Server restart ho gaya!{R}\n")
except KeyboardInterrupt:
    print(f"\n  {G}AsifTechGlobal stopped. Bye!{R}\n")
