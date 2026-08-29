"""
AsifTechGlobal — YouTube API Bot
==================================
YouTube Data API v3 se direct comments karta hai.
Koi Chrome nahi, koi cookies nahi — sirf Google OAuth token!
User Google se login kare → YouTube permission de → Bot automatically kaam kare.
"""

import os, json, time, random, logging, re
from pathlib import Path

try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False

# ── Paths ──────────────────────────────────────────────────────────────────────
_data_dir_env = os.environ.get("BOT_DATA_DIR")
BASE_DIR      = Path(_data_dir_env) if _data_dir_env else Path(__file__).parent.resolve()

TOKEN_FILE    = BASE_DIR / "yt_token.json"
CONFIG_FILE   = BASE_DIR / "config.json"
LOG_FILE      = BASE_DIR / "send_log.txt"
MSGS_FILE     = BASE_DIR / "messages.txt"
URLS_FILE     = BASE_DIR / "urls.txt"

# YouTube API endpoints
YT_LIVECHAT_URL     = "https://www.googleapis.com/youtube/v3/liveBroadcasts"
YT_CHAT_MSG_URL     = "https://www.googleapis.com/youtube/v3/liveChatMessages"
YT_VIDEO_URL        = "https://www.googleapis.com/youtube/v3/videos"
GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

DEFAULT_MESSAGES = [
    "Great stream! 🔥",
    "Amazing content! 👏",
    "Love this! ❤️",
    "Keep it up! 💪",
    "Awesome! 🎉",
    "Great job! 👍",
    "Fantastic! ⭐",
    "So good! 🙌",
]

DEFAULT_CONFIG = {
    "INTERVAL": 20,
    "RANDOM_DELAY": True,
    "MIN_DELAY": 5,
    "MAX_DELAY": 15,
    "LOOP_SETTINGS": {
        "ALLOW_DUPLICATE_MESSAGES": False,
        "BATCH_SLEEP_DELAY": 30
    }
}

# ── Logger ─────────────────────────────────────────────────────────────────────
def setup_logger():
    logger = logging.getLogger("yt_api_bot")
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")
    fh  = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger

# ── Token Management ───────────────────────────────────────────────────────────
def load_token():
    """Load saved OAuth token."""
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_token(token_data):
    """Save OAuth token to file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)

def refresh_access_token(token_data, client_id, client_secret, logger):
    """Refresh expired access token using refresh token."""
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        logger.error("No refresh token available — user needs to re-login")
        return None
    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data={
            "client_id":     client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type":    "refresh_token",
        }, timeout=10)
        new_token = resp.json()
        if "access_token" in new_token:
            # Keep refresh token
            new_token["refresh_token"] = refresh_token
            save_token(new_token)
            logger.info("Access token refreshed successfully")
            return new_token
        else:
            logger.error(f"Token refresh failed: {new_token}")
            return None
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return None

def get_valid_token(logger):
    """Get a valid access token, refreshing if needed."""
    # Load oauth config for client credentials
    _is_cloud = os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT")
    if _is_cloud:
        _base = Path("/tmp/atg_data")
    else:
        _base = Path(__file__).parent.resolve()

    oauth_file = _base.parent / "oauth_config.json" if _is_cloud else Path(__file__).parent / "oauth_config.json"
    # Try multiple locations
    for loc in [Path(__file__).parent / "oauth_config.json",
                Path("/tmp/atg_data/../oauth_config.json"),
                Path(os.environ.get("ATG_APP_DIR", ".")) / "oauth_config.json"]:
        if loc.exists():
            try:
                with open(loc) as f:
                    oc = json.load(f)
                client_id     = oc.get("GOOGLE_CLIENT_ID", "")
                client_secret = oc.get("GOOGLE_CLIENT_SECRET", "")
                break
            except Exception:
                pass
    else:
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    token_data = load_token()
    if not token_data:
        logger.error("No token found — user must login with Google first")
        return None, None

    # Check if token is expired (simple check)
    access_token = token_data.get("access_token")
    if not access_token:
        return None, None

    # Try to verify token
    try:
        r = requests.get(GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}, timeout=5)
        if r.status_code == 401:
            # Token expired — refresh
            logger.info("Token expired, refreshing...")
            token_data = refresh_access_token(token_data, client_id, client_secret, logger)
            if token_data:
                access_token = token_data.get("access_token")
            else:
                return None, None
    except Exception:
        pass

    return access_token, token_data

# ── YouTube API helpers ────────────────────────────────────────────────────────
def get_live_chat_id(video_url, access_token, logger):
    """Get liveChatId from a YouTube video URL."""
    # Extract video ID
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", video_url)
    if not match:
        logger.error(f"Invalid YouTube URL: {video_url}")
        return None
    video_id = match.group(1)

    try:
        r = requests.get(YT_VIDEO_URL, params={
            "part": "liveStreamingDetails",
            "id":   video_id,
        }, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        data = r.json()
        items = data.get("items", [])
        if not items:
            logger.warning(f"Video not found or not live: {video_id}")
            return None
        live_details = items[0].get("liveStreamingDetails", {})
        chat_id = live_details.get("activeLiveChatId")
        if not chat_id:
            logger.warning(f"No active live chat found for: {video_id}")
            return None
        logger.info(f"Live chat ID found: {chat_id}")
        return chat_id
    except Exception as e:
        logger.error(f"Error getting live chat ID: {e}")
        return None

def send_chat_message(chat_id, message, access_token, logger):
    """Send a message to YouTube live chat."""
    try:
        r = requests.post(YT_CHAT_MSG_URL,
            params={"part": "snippet"},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            json={
                "snippet": {
                    "liveChatId": chat_id,
                    "type":       "textMessageEvent",
                    "textMessageDetails": {"messageText": message},
                }
            },
            timeout=10,
        )
        if r.status_code in (200, 201):
            logger.info(f"Sent: {message}")
            return True
        else:
            err = r.json()
            logger.error(f"Send failed ({r.status_code}): {err}")
            # Check for quota exceeded
            if r.status_code == 403:
                errors = err.get("error", {}).get("errors", [])
                for e in errors:
                    if "quotaExceeded" in e.get("reason", ""):
                        logger.error("YouTube API quota exceeded! Try again tomorrow.")
                        return "quota"
            return False
    except Exception as e:
        logger.error(f"Send error: {e}")
        return False

# ── Main Bot ───────────────────────────────────────────────────────────────────
def start_bot():
    logger = setup_logger()
    logger.info("=" * 50)
    logger.info("AsifTechGlobal — YouTube API Bot Starting")
    logger.info("=" * 50)

    if not HAVE_REQUESTS:
        logger.error("requests library not installed! Run: pip install requests")
        return

    # Load config
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg.update(json.load(f))
        except Exception:
            pass

    # Load URLs
    if not URLS_FILE.exists() or not URLS_FILE.read_text().strip():
        logger.error("urls.txt is empty — add YouTube live URLs first!")
        return
    urls = [u.strip() for u in URLS_FILE.read_text().splitlines() if u.strip()]

    # Load messages
    messages = DEFAULT_MESSAGES.copy()
    if MSGS_FILE.exists() and MSGS_FILE.read_text().strip():
        custom = [m.strip() for m in MSGS_FILE.read_text().splitlines() if m.strip()]
        if custom:
            messages = custom

    # Get valid token
    access_token, token_data = get_valid_token(logger)
    if not access_token:
        logger.error("=" * 50)
        logger.error("LOGIN REQUIRED!")
        logger.error("Panel mein Google se login karo")
        logger.error("aur YouTube permission allow karo.")
        logger.error("=" * 50)
        return

    logger.info(f"Loaded {len(urls)} URLs, {len(messages)} messages")
    logger.info("Bot running — press Stop to end")

    # Get live chat IDs for all URLs
    chat_ids = {}
    for url in urls:
        cid = get_live_chat_id(url, access_token, logger)
        if cid:
            chat_ids[url] = cid

    if not chat_ids:
        logger.error("No active live streams found! Make sure URLs are live.")
        return

    allow_dup  = cfg.get("LOOP_SETTINGS", {}).get("ALLOW_DUPLICATE_MESSAGES", False)
    sent_history = set()
    interval   = cfg.get("INTERVAL", 20)
    min_delay  = cfg.get("MIN_DELAY", 5)
    max_delay  = cfg.get("MAX_DELAY", 15)
    rand_delay = cfg.get("RANDOM_DELAY", True)

    round_num = 0
    while True:
        round_num += 1
        logger.info(f"── Round {round_num} ──")

        for url, chat_id in list(chat_ids.items()):
            # Refresh token if needed
            access_token, token_data = get_valid_token(logger)
            if not access_token:
                logger.error("Token expired — stopping bot")
                return

            # Choose message
            candidates = messages if allow_dup else [m for m in messages if m not in sent_history]
            if not candidates:
                sent_history.clear()
                candidates = messages

            msg = random.choice(candidates)

            result = send_chat_message(chat_id, msg, access_token, logger)
            if result == "quota":
                logger.error("API quota exceeded — stopping bot")
                return
            elif result:
                sent_history.add(msg)
            elif not result:
                # Chat might have ended — try to get new chat ID
                logger.warning(f"Retrying chat ID for: {url}")
                new_cid = get_live_chat_id(url, access_token, logger)
                if new_cid:
                    chat_ids[url] = new_cid
                else:
                    logger.warning(f"Stream ended — removing: {url}")
                    del chat_ids[url]
                    if not chat_ids:
                        logger.info("All streams ended. Bot stopped.")
                        return

            # Delay between messages
            delay = random.randint(min_delay, max_delay) if rand_delay else interval
            time.sleep(delay)

        # Batch sleep between rounds
        batch_sleep = cfg.get("LOOP_SETTINGS", {}).get("BATCH_SLEEP_DELAY", 30)
        logger.info(f"Round {round_num} done. Sleeping {batch_sleep}s...")
        time.sleep(batch_sleep)


if __name__ == "__main__":
    start_bot()
