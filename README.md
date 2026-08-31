# AsifTechGlobal — YT Bot Panel (repaired startup edition)

A Flask control panel for configuring a YouTube Live bot per signed-in user. This repaired version focuses on reliable installation, transparent bot-start errors, and safe handling of local configuration.

> **Use responsibly.** Automated activity may breach YouTube rules, and channel owners are responsible for the accounts and streams they control.

## What was fixed

- Added missing desktop runtime dependencies: `selenium` and `webdriver-manager`.
- Reworked `START_SERVER.bat` so a double-click installs/checks dependencies and opens the intended launcher.
- Repaired first-run setup: `config.json` and `oauth_config.json` are now created from the tracked example files.
- Replaced the EXE build command that referenced a missing `AsifTechGlobal.spec` file.
- Fixed the Flask database initialization order, eliminating the previous `init_db is not defined` startup warning.
- Added `bot_runner.py`: import, driver, and runtime crashes are written to **Logs** instead of being silently hidden.
- Removed session-cookie values that had been embedded in the mobile backend. See `SECURITY_NOTICE.md`.

## Windows — quickest start

### Prerequisites

1. Install **Python 3.10+** and tick **Add Python to PATH** during installation.
2. Install Google Chrome when using **Desktop mode**.
3. Download/clone this folder.

### Start

Double-click `START_SERVER.bat`.

It installs the dependencies listed in `requirements.txt`, creates missing local config files, starts the panel, and opens:

- PC: `http://localhost:5000`
- Phone on the same Wi-Fi: the `http://<local-IP>:5000` address printed in the console.

Alternatively, run these commands in Command Prompt from this folder:

```bat
python -m pip install -r requirements.txt
python app.py
```

## Configure before pressing Start

1. Register a panel account and sign in.
2. Add at least one active YouTube Live URL in **Streams**.
3. Add/edit messages in **Messages**.
4. In **Settings**, choose an appropriate interval and save.
5. Press **Start Bot**.
6. Open **Logs** if the bot stops or does not open Chrome.

The panel now rejects a start request with no stream URL and reports fast subprocess failures directly in Logs. Common examples include a missing Chrome installation, a failed ChromeDriver download, expired authentication, or a non-live URL.

## Authentication modes

- **Desktop mode:** uses the local Chrome profile. Chrome must be installed.
- **Cloud/headless mode:** requires an explicitly saved YouTube session cookie or a supported Google OAuth token. It never falls back to a cookie embedded in source code.
- **Google OAuth:** copy `oauth_config.example.json` to `oauth_config.json`, add your own OAuth client credentials, and configure the exact callback URL displayed by your deployment.

Never commit `oauth_config.json`, `.secret_key`, `users.db`, `user_data/`, or browser/session cookies.

## Build a portable Windows EXE

Run `build_exe.bat` on Windows. It installs PyInstaller, bundles the templates/static files plus required Python modules, and writes:

```text
dist\AsifTechGlobal.exe
```

The old build script could not work because it expected `AsifTechGlobal.spec`, but that file was not included in the repository. The repaired script builds directly from `app.py`.

## Railway / Render deployment

The provided `Procfile` and `railway.json` start:

```text
gunicorn web_panel:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

Use environment variables for deployment secrets rather than putting them in files:

- `ATG_ADMIN_KEY` — a strong, unique admin key (do not leave the sample default in production).
- `ATG_BOT_TOKEN` — a strong, unique internal bot token.
- `YT_DEFAULT_COOKIES` — only if you intentionally operate the cookie-based mode and understand the account-security implications.

The cloud file system may be temporary. Do not rely on its SQLite user data for production persistence.

## Verify the repair locally

Run the smoke test after dependencies are installed:

```bash
python smoke_test.py
```

It verifies Python compilation, Flask import/bootstrap, registration, authenticated API access, and the safe “no stream URL” rejection. It intentionally does **not** contact YouTube or start a browser.

## Security action

Read `SECURITY_NOTICE.md` before publishing this project. If the old public repository contained real session cookies, revoke those sessions immediately and clean them from Git history.
