"""
AsifTechGlobal — Android / Termux Entry Point
Chrome ya PC ki zaroorat nahi — sirf mobile phone chahiye!

Run karne ka tarika:
  python termux_app.py
"""

import os
import sys
import time
import socket
import threading
from pathlib import Path

# ─── UTF-8 fix ────────────────────────────────────────────────────────────────
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ─── Paths ────────────────────────────────────────────────────────────────────
BUNDLE_DIR = Path(__file__).parent.resolve()
APP_DIR    = Path(os.environ.get("HOME", os.path.expanduser("~"))) / "AsifTechGlobal"
APP_DIR.mkdir(parents=True, exist_ok=True)

os.environ["ATG_BUNDLE_DIR"] = str(BUNDLE_DIR)
os.environ["ATG_APP_DIR"]    = str(APP_DIR)
os.environ["ATG_HEADLESS"]   = "1"   # API mode: bot_headless.py use hoga

os.chdir(str(APP_DIR))
sys.path.insert(0, str(BUNDLE_DIR))


# ─── Copy defaults ────────────────────────────────────────────────────────────
def _copy_defaults():
    for name in ("config.json", "oauth_config.json"):
        src = BUNDLE_DIR / name
        dst = APP_DIR / name
        if src.exists() and not dst.exists():
            import shutil
            shutil.copy2(src, dst)

_copy_defaults()


# ─── Get IP ───────────────────────────────────────────────────────────────────
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

ip = get_ip()

# ─── Banner ───────────────────────────────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════╗")
print("║    AsifTechGlobal — Android Bot (Termux)     ║")
print("╠══════════════════════════════════════════════╣")
print(f"║  Browser mein kholo: http://localhost:5000   ║")
print(f"║  Same WiFi pe:  http://{ip}:5000".ljust(47) + "║")
print("╠══════════════════════════════════════════════╣")
print("║  Mode: YouTube API (Chrome nahi chahiye)     ║")
print("╚══════════════════════════════════════════════╝")
print()


# ─── Server ───────────────────────────────────────────────────────────────────
def run_server():
    from web_panel import app as flask_app, init_db, USER_DATA
    init_db()
    USER_DATA.mkdir(parents=True, exist_ok=True)
    flask_app.run(host="0.0.0.0", port=5000, debug=False,
                  threaded=True, use_reloader=False)


def start_server_thread():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    return t


print("Server start ho raha hai", end="", flush=True)
server_thread = start_server_thread()

for _ in range(6):
    time.sleep(0.5)
    print(".", end="", flush=True)
print(" Ready!\n")

print("  Bot Panel: http://localhost:5000")
print("  Termux mein band karna ho to: Ctrl + C")
print()

# ─── Keep alive + auto-restart ────────────────────────────────────────────────
try:
    while True:
        time.sleep(3)
        if not server_thread.is_alive():
            print("Server band ho gaya! Restart ho raha hai...")
            time.sleep(2)
            server_thread = start_server_thread()
            print("Server restart ho gaya!")
except KeyboardInterrupt:
    print("\nAsifTechGlobal stopped. Bye!")
