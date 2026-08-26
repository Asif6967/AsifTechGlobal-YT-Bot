# -*- coding: utf-8 -*-
"""
AsifTechGlobal — Headless Bot (Android/Termux Mode)
YouTube Data API v3 se messages bhejta hai — Chrome/Selenium ki zaroorat nahi.

Setup:
  1. Google Cloud Console pe project banao
  2. YouTube Data API v3 enable karo
  3. OAuth 2.0 credentials banao (type: Desktop App)
  4. JSON file download karo, naam rakho: yt_credentials.json
  5. yt_credentials.json ko AsifTechGlobal folder mein rakho
"""

import os
import sys
import json
import time
import random
import logging
import re
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
_data_dir_env = os.environ.get("BOT_DATA_DIR")
BASE_DIR      = Path(_data_dir_env) if _data_dir_env else Path(__file__).parent.resolve()

CONFIG_FILE   = BASE_DIR / "config.json"
LOG_FILE      = BASE_DIR / "send_log.txt"
TOKEN_FILE    = BASE_DIR / "yt_token.json"
CREDS_FILE    = BASE_DIR / "yt_credentials.json"

SCOPES = ["https://www.googleapis.com/auth/youtube"]

DEFAULT_CONFIG = {
    "INTERVAL": 15,
    "RANDOM_DELAY": True,
    "MIN_DELAY": 10,
    "MAX_DELAY": 25,
    "LOOP_SETTINGS": {
        "ALLOW_DUPLICATE_MESSAGES": False,
        "BATCH_SLEEP_DELAY": 30
    }
}

# ─── Logger ───────────────────────────────────────────────────────────────────
def setup_logger():
    logger = logging.getLogger("yt_headless")
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

# ─── Config & Data helpers ────────────────────────────────────────────────────
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


def extract_video_id(url):
    """YouTube URL se video ID nikalo"""
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"live/([A-Za-z0-9_-]{11})",
        r"embed/([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None

# ─── Google OAuth ─────────────────────────────────────────────────────────────
def get_credentials(logger):
    """OAuth credentials lao — pehli baar browser/URL se login hoga"""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        logger.error("Google libraries missing! Run:")
        logger.error("  pip install google-auth google-auth-oauthlib google-api-python-client")
        return None

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            pass

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Token refresh ho gaya")
            except Exception as e:
                logger.warning(f"Token refresh failed: {e} — dobara login zaroor hai")
                creds = None

        if not creds:
            if not CREDS_FILE.exists():
                logger.error("=" * 55)
                logger.error("yt_credentials.json nahi mila!")
                logger.error("")
                logger.error("Steps:")
                logger.error("  1. console.cloud.google.com pe jao")
                logger.error("  2. New Project banao")
                logger.error("  3. APIs & Services > YouTube Data API v3 enable karo")
                logger.error("  4. Credentials > OAuth 2.0 Client ID (Desktop App) banao")
                logger.error("  5. JSON download karo — naam rakho: yt_credentials.json")
                logger.error(f"  6. Yahan rakho: {CREDS_FILE}")
                logger.error("=" * 55)
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
                logger.info("=" * 55)
                logger.info("YOUTUBE LOGIN REQUIRED")
                logger.info("Neeche diya URL apne mobile browser mein kholo:")
                logger.info("=" * 55)
                # Console flow: shows URL + asks for code (works headless/Termux)
                creds = flow.run_console()
            except Exception as e:
                logger.error(f"Login failed: {e}")
                return None

        TOKEN_FILE.write_text(creds.to_json())
        logger.info("Login successful! Token save ho gaya.")

    return creds


# ─── YouTube API helpers ──────────────────────────────────────────────────────
def get_live_chat_id(youtube, video_url, logger):
    """Video URL se activeLiveChatId nikalo"""
    vid = extract_video_id(video_url)
    if not vid:
        logger.warning(f"Invalid YouTube URL: {video_url}")
        return None
    try:
        resp  = youtube.videos().list(part="liveStreamingDetails", id=vid).execute()
        items = resp.get("items", [])
        if items:
            cid = items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")
            if cid:
                return cid
            else:
                logger.warning(f"Stream live nahi hai ya chat off hai: {video_url}")
        else:
            logger.warning(f"Video nahi mila: {video_url}")
    except Exception as e:
        logger.error(f"API error (chat ID): {e}")
    return None


def send_chat_message(youtube, live_chat_id, text, logger):
    """Live chat mein message bhejo"""
    try:
        from googleapiclient.errors import HttpError
        youtube.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": live_chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {"messageText": text}
                }
            }
        ).execute()
        return True
    except Exception as e:
        err_str = str(e)
        if "forbidden" in err_str.lower() or "403" in err_str:
            logger.error(f"Permission denied — YouTube account se logged in hona zaroor hai")
        elif "quotaExceeded" in err_str:
            logger.error("API quota khatam ho gaya — kal dobara try karo")
        elif "liveChatEnded" in err_str:
            logger.warning("Live chat khatam ho gaya")
        else:
            logger.error(f"Message send failed: {e}")
        return False


# ─── Main Bot ─────────────────────────────────────────────────────────────────
def start_bot():
    logger = setup_logger()
    logger.info("=" * 55)
    logger.info("AsifTechGlobal — Headless Bot (Android/API Mode)")
    logger.info("=" * 55)

    # Check dependencies
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        logger.error("google-api-python-client install nahi — run:")
        logger.error("  pip install google-api-python-client")
        return

    # Authenticate
    creds = get_credentials(logger)
    if not creds:
        return

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", credentials=creds)
        logger.info("YouTube API connected!")
    except Exception as e:
        logger.error(f"API build failed: {e}")
        return

    # Load URLs
    urls = get_lines("urls.txt")
    if not urls:
        logger.error("urls.txt mein koi URL nahi — pehle URLs daalo!")
        return

    # Get live chat IDs
    logger.info(f"{len(urls)} URL(s) mein live chat dhundh raha hoon...")
    chat_ids = {}
    for url in urls:
        cid = get_live_chat_id(youtube, url, logger)
        if cid:
            chat_ids[url] = cid
            logger.info(f"  OK: {url}")

    if not chat_ids:
        logger.error("Koi bhi live stream active nahi hai — pehle live URLs daalo!")
        return

    logger.info(f"Bot start ho gaya! {len(chat_ids)} stream(s) pe watch kar raha hoon")
    logger.info("-" * 55)

    sent_history = set()

    while True:
        config        = load_config()
        loop_settings = config.get("LOOP_SETTINGS", {})
        urls_now      = get_lines("urls.txt")
        messages      = get_lines("messages.txt")

        if not messages:
            logger.warning("messages.txt mein koi message nahi — add karo!")
            time.sleep(10)
            continue

        # Remove URLs no longer in file
        for url in list(chat_ids.keys()):
            if url not in urls_now:
                del chat_ids[url]
                logger.info(f"URL remove ho gaya: {url}")

        # Add new URLs
        for url in urls_now:
            if url not in chat_ids:
                cid = get_live_chat_id(youtube, url, logger)
                if cid:
                    chat_ids[url] = cid
                    logger.info(f"Naya stream add: {url}")

        if not chat_ids:
            logger.warning("Koi active stream nahi — 30s wait...")
            time.sleep(30)
            continue

        # Choose message
        allow_dup  = loop_settings.get("ALLOW_DUPLICATE_MESSAGES", False)
        candidates = [m for m in messages if allow_dup or m not in sent_history]
        if not candidates:
            sent_history.clear()
            candidates = messages

        msg = random.choice(candidates)

        # Send to all streams
        for idx, (url, chat_id) in enumerate(list(chat_ids.items())):
            logger.info(f"[Stream {idx + 1}/{len(chat_ids)}] Bhej raha hoon: {msg}")
            ok = send_chat_message(youtube, chat_id, msg, logger)
            if ok:
                logger.info(f"[Stream {idx + 1}] Sent OK!")
                sent_history.add(msg)
            else:
                # Try refreshing chat ID (stream might have restarted)
                new_cid = get_live_chat_id(youtube, url, logger)
                if new_cid:
                    chat_ids[url] = new_cid

            if len(chat_ids) > 1:
                delay = (
                    random.randint(config.get("MIN_DELAY", 10), config.get("MAX_DELAY", 25))
                    if config.get("RANDOM_DELAY", True)
                    else config.get("INTERVAL", 15)
                )
                logger.info(f"Next stream se pehle {delay}s ruk raha hoon...")
                time.sleep(delay)

        batch = loop_settings.get("BATCH_SLEEP_DELAY", 30)
        logger.info(f"Round complete | {len(chat_ids)} stream(s) | {batch}s ke baad dobara...")
        time.sleep(batch)


if __name__ == "__main__":
    start_bot()
