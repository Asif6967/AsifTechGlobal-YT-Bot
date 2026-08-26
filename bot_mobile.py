# -*- coding: utf-8 -*-
"""
AsifTechGlobal — Mobile Bot (Cookie Mode)
==========================================
Koi API key nahi, koi Chrome nahi — sirf YouTube browser cookies chahiye!

Cookies kaise lein (Android):
  Firefox Mobile install karo
  → "Cookie Editor" add-on install karo
  → YouTube.com kholain aur login karo
  → Cookie Editor → Export → Header String → Copy
  → Bot Panel → Settings → YouTube Cookies → Paste → Save
"""

import os, sys, json, time, random, logging, re, hashlib, base64
from pathlib import Path

try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False

# ─── Paths ────────────────────────────────────────────────────────────────────
_data_dir_env = os.environ.get("BOT_DATA_DIR")
BASE_DIR      = Path(_data_dir_env) if _data_dir_env else Path(__file__).parent.resolve()

COOKIES_FILE  = BASE_DIR / "yt_cookies.txt"
CONFIG_FILE   = BASE_DIR / "config.json"
LOG_FILE      = BASE_DIR / "send_log.txt"

WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_CONFIG = {
    "INTERVAL": 15, "RANDOM_DELAY": True,
    "MIN_DELAY": 10, "MAX_DELAY": 25,
    "LOOP_SETTINGS": {"ALLOW_DUPLICATE_MESSAGES": False, "BATCH_SLEEP_DELAY": 30}
}

# ─── Logger ───────────────────────────────────────────────────────────────────
def setup_logger():
    logger = logging.getLogger("yt_mobile")
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")
    fh  = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setFormatter(fmt)
    sh  = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

# ─── Helpers ─────────────────────────────────────────────────────────────────
def load_config():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text("utf-8"))
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def get_lines(filename):
    p = BASE_DIR / filename
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text("utf-8", errors="ignore").splitlines() if l.strip()]


def parse_cookie_string(raw: str) -> dict:
    """'name=value; name2=value2' string ko dict mein convert karo"""
    cookies = {}
    for part in raw.split(';'):
        part = part.strip()
        if '=' in part:
            k, v = part.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies


def load_cookies():
    if not COOKIES_FILE.exists():
        return None
    raw = COOKIES_FILE.read_text("utf-8", errors="ignore").strip()
    if not raw:
        return None
    return parse_cookie_string(raw)

# ─── Protobuf encoder for YouTube params ─────────────────────────────────────
def _varint(n: int) -> bytes:
    result = []
    while n >= 0x80:
        result.append((n & 0x7F) | 0x80)
        n >>= 7
    result.append(n)
    return bytes(result)


def _pb_len_field(field_num: int, data: bytes) -> bytes:
    """Protobuf length-delimited field (type=2)"""
    tag = _varint((field_num << 3) | 2)
    return tag + _varint(len(data)) + data


def make_params(live_chat_id: str) -> str:
    """liveChatId ko YouTube API params format mein encode karo"""
    inner  = _pb_len_field(1, live_chat_id.encode("utf-8"))
    outer  = _pb_len_field(1, inner)
    return base64.urlsafe_b64encode(outer).decode().rstrip("=")

# ─── SAPISIDHASH ──────────────────────────────────────────────────────────────
def compute_sapisidhash(cookies_dict: dict):
    """YouTube authorization header banao"""
    sapisid = (
        cookies_dict.get("SAPISID") or
        cookies_dict.get("__Secure-3PAPISID") or
        cookies_dict.get("__Secure-1PAPISID") or ""
    )
    if not sapisid:
        return None
    ts  = int(time.time())
    raw = f"{ts} {sapisid} https://www.youtube.com"
    h   = hashlib.sha1(raw.encode()).hexdigest()
    return f"SAPISIDHASH {ts}_{h}"

# ─── YouTube page scraper ─────────────────────────────────────────────────────
def get_page_context(url: str, session, logger) -> dict:
    """YouTube live page se API key, client version aur live chat ID nikalo"""
    ctx = {"api_key": "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
           "client_version": "2.20240101.00.00",
           "live_chat_id": None}
    try:
        resp = session.get(url, timeout=20)
        txt  = resp.text

        m = re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"', txt)
        if m:
            ctx["api_key"] = m.group(1)

        m = re.search(r'"INNERTUBE_CLIENT_VERSION"\s*:\s*"([^"]+)"', txt)
        if m:
            ctx["client_version"] = m.group(1)

        m = re.search(r'"activeLiveChatId"\s*:\s*"([^"]+)"', txt)
        if m:
            ctx["live_chat_id"] = m.group(1)
        else:
            # Live chat redirect page check
            m2 = re.search(r'"liveChatRenderer".*?"continuations".*?"liveChatReplayContinuationData".*?"continuation"\s*:\s*"([^"]+)"', txt, re.S)
            if not m2:
                logger.warning(f"Live chat ID nahi mila: {url}")

    except Exception as e:
        logger.error(f"Page load failed ({url}): {e}")
    return ctx

# ─── Send message ─────────────────────────────────────────────────────────────
def send_live_chat_message(session, ctx: dict, cookies_dict: dict, message: str, logger) -> bool:
    sapisidhash = compute_sapisidhash(cookies_dict)
    if not sapisidhash:
        logger.error("SAPISID cookie nahi mili — Panel → Settings → YouTube Cookies mein cookies set karo!")
        return False

    endpoint = (
        f"https://www.youtube.com/youtubei/v1/live_chat/send_message"
        f"?key={ctx['api_key']}"
    )

    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": ctx["client_version"],
                "hl": "en",
                "gl": "US",
            }
        },
        "params": make_params(ctx["live_chat_id"]),
        "richMessage": {
            "textSegments": [{"text": message}]
        }
    }

    headers = {
        "Authorization":       sapisidhash,
        "X-Origin":            "https://www.youtube.com",
        "Origin":              "https://www.youtube.com",
        "Referer":             "https://www.youtube.com/",
        "Content-Type":        "application/json",
        "X-Goog-AuthUser":     "0",
        "X-YouTube-Client-Name":    "1",
        "X-YouTube-Client-Version": ctx["client_version"],
    }

    try:
        resp = session.post(endpoint, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if "error" in data:
                code = data["error"].get("code", "?")
                msg  = data["error"].get("message", "Unknown error")
                if code == 403:
                    logger.error("403 Forbidden — cookies expire ho gayi, naye cookies set karo")
                elif code == 401:
                    logger.error("401 — YouTube account se logout ho gaye ho")
                else:
                    logger.error(f"YouTube error {code}: {msg}")
                return False
            return True
        elif resp.status_code == 403:
            logger.error("403 Forbidden — cookies expire hogi, naye cookies lagao")
        elif resp.status_code == 401:
            logger.error("401 Unauthorized — YouTube login required")
        elif resp.status_code == 400:
            logger.error(f"400 Bad Request — {resp.text[:150]}")
        else:
            logger.error(f"HTTP {resp.status_code}: {resp.text[:100]}")
        return False
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return False

# ─── Main bot loop ────────────────────────────────────────────────────────────
def start_bot():
    if not HAVE_REQUESTS:
        print("ERROR: 'requests' library install nahi hai!")
        print("Run: pip install requests")
        return

    logger = setup_logger()
    logger.info("=" * 55)
    logger.info("AsifTechGlobal — Mobile Bot (Cookie Mode)")
    logger.info("No API Key | No Chrome | Sirf cookies chahiye")
    logger.info("=" * 55)

    # Load cookies
    cookies_dict = load_cookies()
    if not cookies_dict:
        logger.error("")
        logger.error("YouTube cookies nahi mili!")
        logger.error("Panel → Settings → YouTube Cookies → Paste → Save")
        logger.error("")
        logger.error("Cookies kaise lein (Android):")
        logger.error("  1. Firefox install karo")
        logger.error("  2. 'Cookie Editor' add-on lagao")
        logger.error("  3. YouTube.com kholo → login karo")
        logger.error("  4. Cookie Editor → Export → Header String → Copy")
        logger.error("  5. Yahan paste karo aur Save karo")
        logger.error("")
        return

    logger.info(f"Cookies loaded ({len(cookies_dict)} cookies)")

    # HTTP session
    session = requests.Session()
    session.cookies.update(cookies_dict)
    session.headers.update({
        "User-Agent":      WEB_UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    })

    # Load URLs
    urls = get_lines("urls.txt")
    if not urls:
        logger.error("urls.txt mein koi URL nahi! YouTube live stream URLs daalo.")
        return

    # Get live chat context for each URL
    logger.info(f"{len(urls)} stream(s) ka context load ho raha hai...")
    contexts = {}
    for url in urls:
        ctx = get_page_context(url, session, logger)
        if ctx["live_chat_id"]:
            contexts[url] = ctx
            logger.info(f"  ✓ Live chat mila: {url[:60]}")
        else:
            logger.warning(f"  ✗ Live chat nahi: {url[:60]}")

    if not contexts:
        logger.error("Koi bhi active live stream nahi mili — live stream URLs daalo!")
        return

    logger.info(f"Bot ready! {len(contexts)} stream(s) pe kaam shuru karta hoon")
    logger.info("-" * 55)

    sent_history: set = set()

    while True:
        config        = load_config()
        loop_settings = config.get("LOOP_SETTINGS", {})
        urls_now      = get_lines("urls.txt")
        messages      = get_lines("messages.txt")

        if not messages:
            logger.warning("messages.txt mein koi message nahi — kuch messages daalo!")
            time.sleep(10)
            continue

        # Reload cookies (user might update them in panel)
        new_cookies = load_cookies()
        if new_cookies:
            cookies_dict = new_cookies
            session.cookies.update(cookies_dict)

        # Remove URLs no longer in file
        for url in list(contexts.keys()):
            if url not in urls_now:
                del contexts[url]
                logger.info(f"URL hata di: {url[:60]}")

        # Add newly added URLs
        for url in urls_now:
            if url not in contexts:
                ctx = get_page_context(url, session, logger)
                if ctx["live_chat_id"]:
                    contexts[url] = ctx
                    logger.info(f"Naya stream add: {url[:60]}")

        if not contexts:
            logger.warning("Koi active stream nahi — 30s wait kar raha hoon...")
            time.sleep(30)
            continue

        # Pick message
        allow_dup  = loop_settings.get("ALLOW_DUPLICATE_MESSAGES", False)
        candidates = [m for m in messages if allow_dup or m not in sent_history]
        if not candidates:
            sent_history.clear()
            candidates = messages

        msg = random.choice(candidates)

        # Send to all streams
        for idx, (url, ctx) in enumerate(list(contexts.items()), 1):
            logger.info(f"[{idx}/{len(contexts)}] Bhej raha hoon: {msg}")
            ok = send_live_chat_message(session, ctx, cookies_dict, msg, logger)

            if ok:
                logger.info(f"  ✓ Sent!")
                sent_history.add(msg)
            else:
                # Try refreshing the live chat ID (stream might have restarted)
                logger.info("  ↻ Live chat ID refresh kar raha hoon...")
                refreshed = get_page_context(url, session, logger)
                if refreshed["live_chat_id"]:
                    contexts[url] = refreshed

            # Delay between streams
            if idx < len(contexts):
                delay = (
                    random.randint(config.get("MIN_DELAY", 10), config.get("MAX_DELAY", 25))
                    if config.get("RANDOM_DELAY", True)
                    else config.get("INTERVAL", 15)
                )
                logger.info(f"  ⏳ {delay}s wait...")
                time.sleep(delay)

        batch = loop_settings.get("BATCH_SLEEP_DELAY", 30)
        logger.info(f"Round done! {len(contexts)} stream(s) | {batch}s baad dobara...")
        time.sleep(batch)


if __name__ == "__main__":
    start_bot()
