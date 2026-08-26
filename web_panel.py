"""
YT Bot Web Control Panel — Multi-user + Google / Facebook / Email Auth
Run:  python web_panel.py
Mobile: http://<PC-IP>:5000
"""

import os, sys, json, time, sqlite3, subprocess, threading, io, zipfile, socket
from pathlib import Path
from flask import (
    Flask, render_template, request, jsonify,
    Response, redirect, url_for, session, send_file
)
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user, login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth

# Support both normal run and PyInstaller .exe bundle
_app_dir    = os.environ.get("ATG_APP_DIR")
_bundle_dir = os.environ.get("ATG_BUNDLE_DIR")
BASE_DIR    = Path(_app_dir)    if _app_dir    else Path(__file__).parent.resolve()
_TMPL_DIR   = str(Path(_bundle_dir) / "templates") if _bundle_dir else None

DB_FILE     = BASE_DIR / "users.db"
USER_DATA   = BASE_DIR / "user_data"
SECRET_FILE = BASE_DIR / ".secret_key"
OAUTH_FILE  = BASE_DIR / "oauth_config.json"

# ── App & persistent secret key ───────────────────────────────────────────────
# Use bundle template folder when frozen (PyInstaller .exe)
app = Flask(__name__, **(dict(template_folder=_TMPL_DIR) if _TMPL_DIR else {}))
app.config["JSON_AS_ASCII"] = False

# ── Fix for HTTPS tunnels (serveo, localhost.run, ngrok) ──────────────────────
app.config["SESSION_COOKIE_SECURE"]   = False   # allow over HTTP tunnel proxy
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"]  = False
app.config["REMEMBER_COOKIE_SAMESITE"]= "Lax"

# Trust proxy headers so Flask sees correct scheme/host
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

if SECRET_FILE.exists():
    app.secret_key = SECRET_FILE.read_bytes()
else:
    _k = os.urandom(32)
    SECRET_FILE.write_bytes(_k)
    app.secret_key = _k

# ── Flask-Login ───────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "login_page"


class User(UserMixin):
    def __init__(self, row):
        self.id     = str(row["id"])
        self.email  = row["email"]
        self.name   = row["name"]
        self.avatar = row["avatar"] or ""


@login_manager.user_loader
def load_user(uid):
    row = _db_by_id(int(uid))
    return User(row) if row else None


# ── Database ──────────────────────────────────────────────────────────────────
def _db():
    c = sqlite3.connect(str(DB_FILE))
    c.row_factory = sqlite3.Row
    return c


FREE_LIMIT   = 1200          # free comments
PLAN_DAYS    = 20            # paid plan duration
PLAN_PRICE   = 20            # ₹20
ADMIN_SECRET = os.environ.get("ATG_ADMIN_KEY", "atgadmin2024")  # admin panel password

def init_db():
    with _db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT    UNIQUE NOT NULL,
                name        TEXT    NOT NULL,
                password    TEXT,
                google_id   TEXT,
                facebook_id TEXT,
                avatar      TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        # ── Monetization columns (added safely) ──
        for col, defn in [
            ("plan",         "TEXT    DEFAULT 'free'"),
            ("plan_expires", "TEXT    DEFAULT NULL"),
            ("sends_used",   "INTEGER DEFAULT 0"),
        ]:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
            except Exception:
                pass  # column already exists
        # ── Activation keys table ──
        c.execute("""
            CREATE TABLE IF NOT EXISTS act_keys (
                key        TEXT PRIMARY KEY,
                created_at TEXT DEFAULT (datetime('now')),
                used_by    INTEGER DEFAULT NULL,
                used_at    TEXT    DEFAULT NULL
            )
        """)
        c.commit()


def _db_by_id(uid):
    with _db() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def _db_by_email(email):
    with _db() as c:
        return c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()


def _db_create(email, name, password=None, google_id=None, facebook_id=None, avatar=None):
    with _db() as c:
        c.execute(
            "INSERT INTO users (email,name,password,google_id,facebook_id,avatar) VALUES(?,?,?,?,?,?)",
            (email, name, password, google_id, facebook_id, avatar)
        )
        c.commit()
        return c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]


# ── Per-user data dirs ────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "PLATFORM": "youtube",
    "INTERVAL": 15,
    "RANDOM_DELAY": True,
    "MIN_DELAY": 3,
    "MAX_DELAY": 6,
    "MAX_TABS": 5,
    "SPEED_MODE": "normal",
    "SPEED_SETTINGS": {
        "slow": {"INTERVAL": 25, "MIN_DELAY": 10, "MAX_DELAY": 20, "BATCH_SLEEP_DELAY": 15},
        "normal": {"INTERVAL": 15, "MIN_DELAY": 3, "MAX_DELAY": 6, "BATCH_SLEEP_DELAY": 6},
        "fast": {"INTERVAL": 8, "MIN_DELAY": 2, "MAX_DELAY": 4, "BATCH_SLEEP_DELAY": 3},
        "turbo": {"INTERVAL": 4, "MIN_DELAY": 1, "MAX_DELAY": 2, "BATCH_SLEEP_DELAY": 2},
    },
    "ANTI_BAN_SETTINGS": {"HUMAN_SCROLL": True, "MOUSE_MOVE_EMULATION": True},
    "LOOP_SETTINGS": {"BATCH_SLEEP_DELAY": 6, "ALLOW_DUPLICATE_MESSAGES": False},
    "SYSTEM_SETTINGS": {"HEADLESS_MODE": False}
}


def u_dir(uid):
    d = USER_DATA / str(uid)
    d.mkdir(parents=True, exist_ok=True)
    return d


def u_file(uid, name):
    return u_dir(uid) / name


def ensure_user_data(uid):
    cfg = u_file(uid, "config.json")
    if not cfg.exists():
        cfg.write_text(json.dumps(DEFAULT_CONFIG, indent=4))
    for fname in ("urls.txt", "messages.txt", "send_log.txt"):
        fp = u_file(uid, fname)
        if not fp.exists():
            fp.write_text("")


# ── OAuth ─────────────────────────────────────────────────────────────────────
def _load_oc():
    if OAUTH_FILE.exists():
        with open(OAUTH_FILE) as f:
            return json.load(f)
    return {}


_oc = _load_oc()
oauth = OAuth(app)

google_oauth = None
if _oc.get("GOOGLE_CLIENT_ID") and _oc.get("GOOGLE_CLIENT_SECRET"):
    google_oauth = oauth.register(
        name="google",
        client_id=_oc["GOOGLE_CLIENT_ID"],
        client_secret=_oc["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

facebook_oauth = None
if _oc.get("FACEBOOK_APP_ID") and _oc.get("FACEBOOK_APP_SECRET"):
    facebook_oauth = oauth.register(
        name="facebook",
        client_id=_oc["FACEBOOK_APP_ID"],
        client_secret=_oc["FACEBOOK_APP_SECRET"],
        access_token_url="https://graph.facebook.com/oauth/access_token",
        authorize_url="https://www.facebook.com/dialog/oauth",
        api_base_url="https://graph.facebook.com/",
        client_kwargs={"scope": "email,public_profile"},
    )


# ── Dynamic OAuth helpers (lazy-init — no server restart needed after credential save) ──
def _ensure_google_oauth():
    """Return Google OAuth client, registering it on-the-fly if credentials were saved after startup."""
    global google_oauth
    if google_oauth is not None:
        return google_oauth
    oc = _load_oc()
    cid  = oc.get("GOOGLE_CLIENT_ID", "")
    csec = oc.get("GOOGLE_CLIENT_SECRET", "")
    if not cid or not csec:
        return None
    try:
        if "google" in getattr(oauth, "_clients", {}):
            google_oauth = oauth._clients["google"]
        else:
            google_oauth = oauth.register(
                name="google",
                client_id=cid,
                client_secret=csec,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
    except Exception:
        google_oauth = None
    return google_oauth


def _ensure_facebook_oauth():
    """Return Facebook OAuth client, registering it on-the-fly if credentials were saved after startup."""
    global facebook_oauth
    if facebook_oauth is not None:
        return facebook_oauth
    oc = _load_oc()
    fid  = oc.get("FACEBOOK_APP_ID", "")
    fsec = oc.get("FACEBOOK_APP_SECRET", "")
    if not fid or not fsec:
        return None
    try:
        if "facebook" in getattr(oauth, "_clients", {}):
            facebook_oauth = oauth._clients["facebook"]
        else:
            facebook_oauth = oauth.register(
                name="facebook",
                client_id=fid,
                client_secret=fsec,
                access_token_url="https://graph.facebook.com/oauth/access_token",
                authorize_url="https://www.facebook.com/dialog/oauth",
                api_base_url="https://graph.facebook.com/",
                client_kwargs={"scope": "email,public_profile"},
            )
    except Exception:
        facebook_oauth = None
    return facebook_oauth


# ── Plan helpers ─────────────────────────────────────────────────────────────

def _get_plan(uid):
    """Return plan info dict for a user."""
    from datetime import datetime as _dt2
    row = _db_by_id(int(uid))
    if not row:
        return {"plan": "free", "sends_used": 0, "active": False, "expires": None, "remaining": FREE_LIMIT}
    plan       = row["plan"] or "free"
    sends_used = row["sends_used"] or 0
    expires    = row["plan_expires"]
    now        = _dt2.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    active     = (plan == "paid" and expires and expires > now)
    if plan == "paid" and expires and expires <= now:
        # Plan expired — reset to free
        with _db() as c:
            c.execute("UPDATE users SET plan='free', plan_expires=NULL WHERE id=?", (int(uid),))
            c.commit()
        plan   = "free"
        active = False
    remaining = None if active else max(0, FREE_LIMIT - sends_used)
    return {
        "plan":       plan,
        "active":     active,
        "sends_used": sends_used,
        "expires":    expires,
        "remaining":  remaining,
        "free_limit": FREE_LIMIT,
        "plan_days":  PLAN_DAYS,
        "plan_price": PLAN_PRICE,
    }


def _can_send(uid):
    """Return True if user is allowed to send one more comment."""
    p = _get_plan(uid)
    if p["active"]:
        return True
    return p["remaining"] > 0


def _deduct_send(uid):
    """Increment sends_used by 1. Return new count."""
    with _db() as c:
        c.execute("UPDATE users SET sends_used = sends_used + 1 WHERE id=?", (int(uid),))
        c.commit()
        row = c.execute("SELECT sends_used FROM users WHERE id=?", (int(uid),)).fetchone()
        return row["sends_used"] if row else 0


# ── Bot process registry ─────────────────────────────────────────────────────
_bots: dict = {}  # uid -> Popen
_bot_lock = threading.Lock()


def _bot_running(uid):
    p = _bots.get(str(uid))
    return p is not None and p.poll() is None


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_template(
        "login.html",
        google_on=_ensure_google_oauth() is not None,
        facebook_on=_ensure_facebook_oauth() is not None,
        error=request.args.get("error", ""),
    )


@app.route("/auth/login", methods=["POST"])
def auth_login():
    d = request.json or {}
    email = d.get("email", "").strip().lower()
    pw    = d.get("password", "")
    if not email or not pw:
        return jsonify({"ok": False, "msg": "Email and password required"})
    row = _db_by_email(email)
    if not row or not row["password"] or not check_password_hash(row["password"], pw):
        return jsonify({"ok": False, "msg": "Invalid email or password"})
    login_user(User(row), remember=True)
    ensure_user_data(row["id"])
    return jsonify({"ok": True})


@app.route("/auth/register", methods=["POST"])
def auth_register():
    d = request.json or {}
    email = d.get("email", "").strip().lower()
    name  = d.get("name", "").strip()
    pw    = d.get("password", "")
    if not email or not name or not pw:
        return jsonify({"ok": False, "msg": "All fields are required"})
    if len(pw) < 6:
        return jsonify({"ok": False, "msg": "Password must be at least 6 characters"})
    if _db_by_email(email):
        return jsonify({"ok": False, "msg": "Email already registered"})
    uid = _db_create(email, name, password=generate_password_hash(pw))
    row = _db_by_id(uid)
    login_user(User(row), remember=True)
    ensure_user_data(uid)
    return jsonify({"ok": True})


@app.route("/auth/google")
def auth_google():
    go = _ensure_google_oauth()
    if not go:
        return redirect(url_for("login_page", error="google_not_configured"))
    nonce = os.urandom(16).hex()
    session["_g_nonce"] = nonce
    cb = url_for("auth_google_cb", _external=True)
    return go.authorize_redirect(cb, nonce=nonce)


@app.route("/auth/google/callback")
def auth_google_cb():
    go = _ensure_google_oauth()
    if not go:
        return redirect(url_for("login_page"))
    try:
        token = go.authorize_access_token()
        uinfo = token.get("userinfo") or {}
        if not uinfo:
            uinfo = go.userinfo()
        email  = uinfo.get("email", "").lower()
        name   = uinfo.get("name", email.split("@")[0])
        gid    = uinfo.get("sub", "")
        avatar = uinfo.get("picture", "")
        row = _db_by_email(email)
        if row:
            uid = row["id"]
            if not row["google_id"]:
                with _db() as c:
                    c.execute("UPDATE users SET google_id=?,avatar=? WHERE id=?", (gid, avatar, uid))
                    c.commit()
        else:
            uid = _db_create(email, name, google_id=gid, avatar=avatar)
        login_user(User(_db_by_id(uid)), remember=True)
        ensure_user_data(uid)
        return redirect(url_for("index"))
    except Exception:
        return redirect(url_for("login_page", error="google_failed"))


@app.route("/auth/facebook")
def auth_facebook():
    fo = _ensure_facebook_oauth()
    if not fo:
        return redirect(url_for("login_page", error="facebook_not_configured"))
    cb = url_for("auth_facebook_cb", _external=True)
    return fo.authorize_redirect(cb)


@app.route("/auth/facebook/callback")
def auth_facebook_cb():
    fo = _ensure_facebook_oauth()
    if not fo:
        return redirect(url_for("login_page"))
    try:
        token = fo.authorize_access_token()
        resp  = fo.get("me?fields=id,name,email,picture.type(large)")
        uinfo = resp.json()
        email  = uinfo.get("email", f"fb_{uinfo['id']}@fb.local").lower()
        name   = uinfo.get("name", "User")
        fb_id  = uinfo["id"]
        pic    = uinfo.get("picture", {})
        avatar = pic.get("data", {}).get("url", "") if isinstance(pic, dict) else ""
        row = _db_by_email(email)
        uid = row["id"] if row else _db_create(email, name, facebook_id=fb_id, avatar=avatar)
        login_user(User(_db_by_id(uid)), remember=True)
        ensure_user_data(uid)
        return redirect(url_for("index"))
    except Exception:
        return redirect(url_for("login_page", error="facebook_failed"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ══════════════════════════════════════════════════════════════════════════════
#  BOT + DATA APIs  (all require login, scoped per user)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/me")
@login_required
def api_me():
    return jsonify({
        "name":   current_user.name,
        "email":  current_user.email,
        "avatar": current_user.avatar,
    })


@app.route("/api/status")
@login_required
def api_status():
    return jsonify({"running": _bot_running(current_user.id)})


@app.route("/api/start", methods=["POST"])
@login_required
def api_start():
    uid = current_user.id
    with _bot_lock:
        if _bot_running(uid):
            return jsonify({"ok": False, "msg": "Bot already running"})
        log_f = u_file(uid, "send_log.txt")
        with open(log_f, "w", encoding="utf-8") as _lf:
            pass
        env = os.environ.copy()
        env["BOT_DATA_DIR"] = str(u_dir(uid))
        # Headless/Android mode: use bot_mobile.py (Cookie-based, no Selenium, no API key)
        is_headless = os.environ.get("ATG_HEADLESS") == "1"
        if is_headless:
            cmd = [sys.executable, "-c", "from bot_mobile import start_bot; start_bot()"]
        # When frozen (.exe), pass --bot-mode flag; else use -c
        elif getattr(sys, "frozen", False):
            cmd = [sys.executable, "--bot-mode", str(u_dir(uid))]
        else:
            cmd = [sys.executable, "-c", "from bot import start_bot; start_bot()"]
        proc = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        _bots[str(uid)] = proc
    return jsonify({"ok": True, "msg": "Bot started"})


@app.route("/api/stop", methods=["POST"])
@login_required
def api_stop():
    uid = current_user.id
    with _bot_lock:
        if not _bot_running(uid):
            return jsonify({"ok": False, "msg": "Bot not running"})
        proc = _bots.pop(str(uid), None)
        if proc:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                )
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
    return jsonify({"ok": True, "msg": "Bot stopped"})


@app.route("/api/logs")
@login_required
def api_logs():
    uid      = current_user.id
    log_path = u_file(uid, "send_log.txt")

    def gen():
        if not log_path.exists():
            open(log_path, "w").close()
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f.readlines()[-60:]:
                yield f"data: {line.rstrip()}\n\n"
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.rstrip()}\n\n"
                else:
                    time.sleep(0.4)
                    yield ":\n\n"

    return Response(
        gen(), mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _read_lines(path):
    p = Path(path)
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _write_lines(path, lines):
    Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


# ── URLs ──────────────────────────────────────────────────────────────────────

@app.route("/api/urls", methods=["GET"])
@login_required
def api_urls_get():
    return jsonify(_read_lines(u_file(current_user.id, "urls.txt")))


@app.route("/api/urls", methods=["POST"])
@login_required
def api_urls_add():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"ok": False, "msg": "Empty URL"})
    lines = _read_lines(u_file(current_user.id, "urls.txt"))
    if url not in lines:
        lines.append(url)
        _write_lines(u_file(current_user.id, "urls.txt"), lines)
    return jsonify({"ok": True})


@app.route("/api/urls", methods=["DELETE"])
@login_required
def api_urls_del():
    target = (request.json or {}).get("url", "").strip()
    lines  = [l for l in _read_lines(u_file(current_user.id, "urls.txt")) if l != target]
    _write_lines(u_file(current_user.id, "urls.txt"), lines)
    return jsonify({"ok": True})


# ── Messages ──────────────────────────────────────────────────────────────────

@app.route("/api/messages", methods=["GET"])
@login_required
def api_msg_get():
    return jsonify(_read_lines(u_file(current_user.id, "messages.txt")))


@app.route("/api/messages", methods=["POST"])
@login_required
def api_msg_add():
    msg = (request.json or {}).get("message", "").strip()
    if not msg:
        return jsonify({"ok": False, "msg": "Empty message"})
    lines = _read_lines(u_file(current_user.id, "messages.txt"))
    lines.append(msg)
    _write_lines(u_file(current_user.id, "messages.txt"), lines)
    return jsonify({"ok": True})


@app.route("/api/messages", methods=["DELETE"])
@login_required
def api_msg_del():
    target = (request.json or {}).get("message", "").strip()
    lines  = [l for l in _read_lines(u_file(current_user.id, "messages.txt")) if l != target]
    _write_lines(u_file(current_user.id, "messages.txt"), lines)
    return jsonify({"ok": True})


# ── Config ────────────────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
@login_required
def api_cfg_get():
    f = u_file(current_user.id, "config.json")
    if not Path(f).exists():
        return jsonify(DEFAULT_CONFIG)
    with open(f) as fh:
        return jsonify(json.load(fh))


@app.route("/api/config", methods=["POST"])
@login_required
def api_cfg_save():
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"ok": False, "msg": "Invalid data"})
    with open(u_file(current_user.id, "config.json"), "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return jsonify({"ok": True})


# ── OAuth config (save credentials for Google/FB setup) ───────────────────────

@app.route("/api/oauth-status")
def api_oauth_status():
    """Public endpoint — check which OAuth providers are currently configured."""
    return jsonify({
        "google":   _ensure_google_oauth()   is not None,
        "facebook": _ensure_facebook_oauth() is not None,
    })


@app.route("/api/oauth-save", methods=["POST"])
def api_oauth_save():
    """Save OAuth credentials and hot-reload clients — no server restart needed."""
    global google_oauth, facebook_oauth
    data = request.json or {}
    existing = {}
    if OAUTH_FILE.exists():
        with open(OAUTH_FILE) as f:
            existing = json.load(f)
    existing.update({k: v for k, v in data.items() if v})
    with open(OAUTH_FILE, "w") as f:
        json.dump(existing, f, indent=4)
    # Wipe cached clients so _ensure_*() re-registers with new credentials
    google_oauth   = None
    facebook_oauth = None
    if hasattr(oauth, "_clients"):
        oauth._clients.pop("google",   None)
        oauth._clients.pop("facebook", None)
    # Eagerly register so the next login request works immediately
    _ensure_google_oauth()
    _ensure_facebook_oauth()
    return jsonify({"ok": True, "msg": "Saved! Google/Facebook login is now active.", "reload": True})


# ── Static files ────────────────────────────────────────────────────────────
import mimetypes

@app.route("/static/<path:filename>")
def static_files(filename):
    static_dir = Path(os.environ.get("ATG_BUNDLE_DIR", str(BASE_DIR))) / "static"
    fp = static_dir / filename
    if not fp.exists():
        return "", 404
    mt, _ = mimetypes.guess_type(str(fp))
    return send_file(str(fp), mimetype=mt or "application/octet-stream")


# ── Android Download ──────────────────────────────────────────────────────────

def _get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


@app.route("/download")
def download_page():
    ip  = _get_local_ip()
    url = f"http://{ip}:5000/download/android"
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AsifTechGlobal — Android Download</title>
<style>
  body{{margin:0;background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px;box-sizing:border-box}}
  .box{{max-width:420px;width:100%;text-align:center}}
  h1{{color:#00ff88;font-size:22px;margin-bottom:6px}}
  p{{color:#8b949e;font-size:13px;margin-bottom:24px}}
  .qr{{background:#fff;padding:12px;border-radius:12px;display:inline-block;margin-bottom:20px}}
  .btn{{display:block;background:#238636;color:#fff;text-decoration:none;padding:15px;border-radius:10px;font-size:16px;font-weight:700;margin-bottom:12px}}
  .url{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:10px;font-size:11px;font-family:monospace;color:#79c0ff;word-break:break-all;margin-bottom:20px}}
  .steps{{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:16px;text-align:left;font-size:13px;line-height:1.8;color:#8b949e}}
  .steps b{{color:#e6edf3}}
</style>
</head><body>
<div class="box">
  <h1>📱 AsifTechGlobal Android</h1>
  <p>QR scan karo ya neeche button se download karo</p>

  <div class="qr">
    <img src="https://api.qrserver.com/v1/create-qr-code/?size=180x180&data={url}" width="180" height="180" alt="QR Code">
  </div>
  <br>

  <a class="btn" href="/download/android">⬇ Download Android Package</a>

  <div class="url">{url}</div>

  <div class="steps">
    <b>Setup Steps (Phone pe):</b><br>
    1. Termux install karo (Play Store / F-Droid)<br>
    2. ZIP download karo<br>
    3. Termux mein:<br>
    &nbsp;&nbsp;<code style="color:#00ff88">termux-setup-storage</code><br>
    &nbsp;&nbsp;<code style="color:#00ff88">cp /sdcard/Download/AsifTechGlobal_Android.zip ~/</code><br>
    &nbsp;&nbsp;<code style="color:#00ff88">cd ~/ &amp;&amp; unzip AsifTechGlobal_Android.zip -d bot</code><br>
    &nbsp;&nbsp;<code style="color:#00ff88">cd bot &amp;&amp; bash termux_setup.sh</code><br>
    &nbsp;&nbsp;<code style="color:#00ff88">python termux_app.py</code>
  </div>
</div>
</body></html>"""


@app.route("/download/android")
def download_android():
    """Android/Termux package ZIP serve karo"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        android_files = [
            "termux_app.py", "termux_setup.sh", "bot_mobile.py",
            "web_panel.py", "config.json", "oauth_config.json",
        ]
        for fname in android_files:
            p = BASE_DIR / fname
            if p.exists():
                zf.write(p, fname)
        # Templates folder
        tmpl = BASE_DIR / "templates"
        if tmpl.exists():
            for f in tmpl.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(BASE_DIR))
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="AsifTechGlobal_Android.zip",
        mimetype="application/zip",
    )


# ── YouTube Cookies (Mobile/headless mode) ────────────────────────────────────

@app.route("/api/cookies", methods=["GET"])
@login_required
def api_cookies_get():
    uid  = current_user.id
    path = u_file(uid, "yt_cookies.txt")
    raw  = path.read_text("utf-8", errors="ignore").strip() if path.exists() else ""
    # Mask all values for display: show only key names
    masked = ""
    if raw:
        parts  = [p.strip() for p in raw.split(";") if "=" in p.strip()]
        masked = "; ".join(k.split("=", 1)[0].strip() for k in parts)
    return jsonify({"has_cookies": bool(raw), "cookie_keys": masked, "count": len([p for p in raw.split(";") if "=" in p]) if raw else 0})


@app.route("/api/cookies", methods=["POST"])
@login_required
def api_cookies_save():
    raw = (request.json or {}).get("cookies", "").strip()
    if not raw:
        return jsonify({"ok": False, "msg": "Cookies empty hain"})
    # Basic validation — must contain at least one key=value pair
    if "=" not in raw:
        return jsonify({"ok": False, "msg": "Invalid format — 'name=value; ...' format mein hona chahiye"})
    path = u_file(current_user.id, "yt_cookies.txt")
    path.write_text(raw, encoding="utf-8")
    count = len([p for p in raw.split(";") if "=" in p.strip()])
    return jsonify({"ok": True, "msg": f"{count} cookies save ho gayi!"})


@app.route("/api/cookies", methods=["DELETE"])
@login_required
def api_cookies_del():
    path = u_file(current_user.id, "yt_cookies.txt")
    if path.exists():
        path.write_text("")
    return jsonify({"ok": True, "msg": "Cookies clear ho gayi"})


# ══════════════════════════════════════════════════════════════════════════════
#  MONETIZATION APIs
# ══════════════════════════════════════════════════════════════════════════════

_BOT_TOKEN = os.environ.get("ATG_BOT_TOKEN", "atgbot2024")

@app.route("/api/internal/use-credit", methods=["POST"])
def api_internal_use_credit():
    """Called by bot process directly — no user session, uses bot token header."""
    if request.headers.get("X-Bot-Token") != _BOT_TOKEN:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 403
    uid = request.headers.get("X-Bot-Uid", "").strip()
    if not uid.isdigit():
        return jsonify({"ok": True})
    p = _get_plan(int(uid))
    if p["active"]:
        return jsonify({"ok": True, "plan": "paid"})
    if p["remaining"] > 0:
        new_count = _deduct_send(int(uid))
        left      = max(0, FREE_LIMIT - new_count)
        return jsonify({"ok": True, "plan": "free", "remaining": left})
    return jsonify({
        "ok":  False, "plan": "free", "remaining": 0,
        "msg": f"Free 1200 comments khatam! Rs.{PLAN_PRICE} mein {PLAN_DAYS} din unlimited upgrade karo — http://localhost:5000/upgrade"
    })

@app.route("/api/plan")
@login_required
def api_plan():
    """Return current user's plan status."""
    return jsonify(_get_plan(current_user.id))


@app.route("/api/use-credit", methods=["POST"])
@login_required
def api_use_credit():
    """Bot calls this after every successful send. Returns ok/blocked."""
    uid = current_user.id
    p   = _get_plan(uid)
    if p["active"]:
        return jsonify({"ok": True, "plan": "paid"})
    if p["remaining"] > 0:
        new_count = _deduct_send(uid)
        left      = max(0, FREE_LIMIT - new_count)
        return jsonify({"ok": True, "plan": "free", "remaining": left})
    return jsonify({"ok": False, "plan": "free", "remaining": 0,
                    "msg": "Free limit khatam! ₹20 mein 20 din unlimited upgrade karo."})


@app.route("/api/activate-plan", methods=["POST"])
@login_required
def api_activate_plan():
    """Activate paid plan using a key."""
    from datetime import datetime as _dt2, timedelta
    data = request.json or {}
    key  = data.get("key", "").strip().upper()
    if not key:
        return jsonify({"ok": False, "msg": "Key enter karo"})
    uid = int(current_user.id)
    with _db() as c:
        row = c.execute("SELECT * FROM act_keys WHERE key=?", (key,)).fetchone()
        if not row:
            return jsonify({"ok": False, "msg": "Invalid key — dobara check karo"})
        if row["used_by"]:
            return jsonify({"ok": False, "msg": "Yeh key already use ho chuki hai"})
        expires = (_dt2.utcnow() + timedelta(days=PLAN_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
        now     = _dt2.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE act_keys SET used_by=?, used_at=? WHERE key=?", (uid, now, key))
        c.execute("UPDATE users SET plan='paid', plan_expires=? WHERE id=?", (expires, uid))
        c.commit()
    return jsonify({"ok": True,
                    "msg": f"✅ Plan active! {PLAN_DAYS} din unlimited comments.",
                    "expires": expires})


# ── Public payment info page ──────────────────────────────────────────────────

@app.route("/upgrade")
def upgrade_page():
    """Public upgrade/payment info page."""
    return render_template("upgrade.html")


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN PANEL  (protected by ADMIN_SECRET key)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin")
def admin_page():
    if request.args.get("key") != ADMIN_SECRET:
        return "Access Denied", 403
    with _db() as c:
        users = c.execute(
            "SELECT id,email,name,plan,plan_expires,sends_used,created_at FROM users ORDER BY id DESC"
        ).fetchall()
        keys  = c.execute(
            "SELECT k.key,k.created_at,k.used_at,u.email as used_by_email "
            "FROM act_keys k LEFT JOIN users u ON k.used_by=u.id ORDER BY k.created_at DESC"
        ).fetchall()
    return render_template("admin.html", users=users, keys=keys,
                           free_limit=FREE_LIMIT, plan_days=PLAN_DAYS, plan_price=PLAN_PRICE,
                           admin_key=ADMIN_SECRET)


@app.route("/admin/gen-key", methods=["POST"])
def admin_gen_key():
    if request.json.get("key") != ADMIN_SECRET:
        return jsonify({"ok": False}), 403
    import secrets as _sec
    new_key = "ATG-" + _sec.token_hex(4).upper() + "-" + _sec.token_hex(3).upper()
    count   = int(request.json.get("count", 1))
    keys    = []
    with _db() as c:
        for _ in range(min(count, 50)):
            k = "ATG-" + _sec.token_hex(4).upper() + "-" + _sec.token_hex(3).upper()
            c.execute("INSERT OR IGNORE INTO act_keys (key) VALUES (?)", (k,))
            keys.append(k)
        c.commit()
    return jsonify({"ok": True, "keys": keys})


@app.route("/admin/reset-user", methods=["POST"])
def admin_reset_user():
    if request.json.get("key") != ADMIN_SECRET:
        return jsonify({"ok": False}), 403
    uid = int(request.json.get("uid", 0))
    with _db() as c:
        c.execute("UPDATE users SET plan='free',plan_expires=NULL,sends_used=0 WHERE id=?", (uid,))
        c.commit()
    return jsonify({"ok": True})


@app.route("/admin/set-plan", methods=["POST"])
def admin_set_plan():
    """Manually give a user paid plan (after manual UPI verification)."""
    from datetime import datetime as _dt2, timedelta
    if request.json.get("key") != ADMIN_SECRET:
        return jsonify({"ok": False}), 403
    uid     = int(request.json.get("uid", 0))
    days    = int(request.json.get("days", PLAN_DAYS))
    expires = (_dt2.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with _db() as c:
        c.execute("UPDATE users SET plan='paid',plan_expires=? WHERE id=?", (expires, uid))
        c.commit()
    return jsonify({"ok": True, "expires": expires})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import socket

    # Windows consoles may default to cp1252 and fail on the banner emoji.
    for _stream in (sys.stdout, sys.stderr):
        if _stream and hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    init_db()
    USER_DATA.mkdir(exist_ok=True)

    def _get_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return socket.gethostbyname(socket.gethostname())

    ip = _get_ip()
    print("\n" + "=" * 54)
    print("  ⚡  YT BOT  —  WEB PANEL  (Multi-user + Auth)")
    print("=" * 54)
    print(f"  PC     : http://localhost:5000")
    print(f"  Mobile : http://{ip}:5000")
    print("=" * 54)
    print("  Register with email/password or Google/Facebook")
    print("  Each user gets their own bot & data (separate)")
    print("=" * 54 + "\n")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
