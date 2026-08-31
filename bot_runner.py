"""Run a selected bot backend and always write fatal startup errors to send_log.txt.

The web panel launches this wrapper instead of importing a backend in a silent
subprocess. This exposes missing libraries, browser-driver failures, and other
startup exceptions in the panel's Log tab.
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


def _log_path() -> Path:
    base = Path(os.environ.get("BOT_DATA_DIR") or Path(__file__).parent)
    base.mkdir(parents=True, exist_ok=True)
    return base / "send_log.txt"


def _write(message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    with _log_path().open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} | {message.rstrip()}\n")


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "desktop").lower()
    modules = {"desktop": "bot", "mobile": "bot_mobile", "api": "youtube_bot"}
    module_name = modules.get(mode)
    if not module_name:
        _write(f"ERROR | Unknown bot mode: {mode}")
        return 2

    _write(f"INFO | Bot process starting in {mode} mode.")
    try:
        module = __import__(module_name, fromlist=["start_bot"])
        module.start_bot()
        _write("INFO | Bot process stopped.")
        return 0
    except Exception:
        _write("ERROR | Bot crashed during startup or operation:")
        for line in traceback.format_exc().rstrip().splitlines():
            _write(f"ERROR | {line}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
