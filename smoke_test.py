"""Offline smoke checks for the repaired control panel.

Run: python smoke_test.py
No browser is launched and no external platform is contacted.
"""

import importlib
import os
import sys
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="atg-smoke-") as data_dir:
        os.environ["ATG_APP_DIR"] = data_dir
        os.environ["ATG_BUNDLE_DIR"] = str(ROOT)
        sys.path.insert(0, str(ROOT))
        panel = importlib.import_module("web_panel")
        client = panel.app.test_client()

        registered = client.post(
            "/auth/register",
            json={"email": "smoke@example.test", "name": "Smoke Test", "password": "safe-pass-123"},
        )
        check(registered.status_code == 200 and registered.get_json().get("ok"), "registration works")
        check(client.get("/api/status").status_code == 200, "authenticated status route works")

        response = client.post("/api/start")
        body = response.get_json() or {}
        check(response.status_code == 400 and not body.get("ok"), "bot safely refuses to start without a stream URL")
        check("URL" in body.get("msg", ""), "missing-stream error explains the fix")

        package = client.get("/download/android")
        with zipfile.ZipFile(BytesIO(package.data)) as archive:
            bundled = set(archive.namelist())
        required = {"termux_app.py", "termux_setup.sh", "bot_runner.py", "config.example.json", "templates/index.html", "static/manifest.json"}
        check(package.status_code == 200 and required.issubset(bundled), "Android download includes runnable sources and assets")

    print("\nAll offline smoke checks passed.")


if __name__ == "__main__":
    main()
