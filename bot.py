# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import random
import logging
import shutil
import threading
import re
import ctypes
import glob

# ─── Windows UTF-8 console fix ────────────────────────────────────────────────
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

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# ─── ANSI COLORS (no pip needed, works in PowerShell & CMD) ───────────────────
if os.name == 'nt':
    os.system('')          # Unlock ANSI escape codes on Windows

R      = '\033[0m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
CYAN   = '\033[96m'
GREEN  = '\033[92m'
YELLOW = '\033[93m'
MAGEN  = '\033[95m'
BLUE   = '\033[94m'
RED    = '\033[91m'
WHITE  = '\033[97m'
AQUA   = '\033[38;5;51m'
LIME   = '\033[38;5;46m'
PINK   = '\033[38;5;201m'
GOLD   = '\033[38;5;226m'
SKY    = '\033[38;5;45m'

# If launched by web_panel (multi-user), BOT_DATA_DIR points to user's data folder
_data_dir_env    = os.environ.get("BOT_DATA_DIR")
BASE_DIR         = os.path.abspath(_data_dir_env) if _data_dir_env else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(BASE_DIR, "config.json")

# ── Monetization: credit check via web panel API ──────────────────────────────
# BOT_DATA_DIR is like  .../user_data/3  — last part is user ID
_uid_from_dir = os.path.basename(BASE_DIR)   # "3"  (or empty if standalone)
_PANEL_URL    = os.environ.get("ATG_PANEL_URL", "http://127.0.0.1:5000")

def _use_credit_api():
    """
    Call /api/use-credit on the web panel using the internal service token.
    Returns (ok: bool, msg: str).
    Called after every successful comment send.
    """
    if not _uid_from_dir.isdigit():
        return True, ""          # standalone run — no limit
    try:
        import urllib.request as _ur, urllib.error as _ue2
        req = _ur.Request(
            f"{_PANEL_URL}/api/internal/use-credit",
            data=b"",
            headers={"X-Bot-Uid": _uid_from_dir,
                     "X-Bot-Token": os.environ.get("ATG_BOT_TOKEN", "atgbot2024")},
            method="POST",
        )
        with _ur.urlopen(req, timeout=4) as resp:
            import json as _json
            d = _json.loads(resp.read())
            return d.get("ok", True), d.get("msg", "")
    except Exception:
        return True, ""          # on error, don't block the bot

DEFAULT_CONFIG = {
    "PLATFORM": "youtube",
    "INTERVAL": 15,
    "RANDOM_DELAY": True,
    "MIN_DELAY": 10,
    "MAX_DELAY": 25,
    "MAX_TABS": 10,
    "LOG_LEVEL": "INFO",
    "ANTI_BAN_SETTINGS": {"HUMAN_SCROLL": True, "MOUSE_MOVE_EMULATION": True},
    "LOOP_SETTINGS": {"BATCH_SLEEP_DELAY": 30, "ALLOW_DUPLICATE_MESSAGES": False},
    "SYSTEM_SETTINGS": {"HEADLESS_MODE": False, "TERMINAL_COLOR": "cyan"}
}

# ══════════════════════════════════════════════════════════════════════════════
#  LIVE RAIN SECTION  (top of terminal, always running)
# ══════════════════════════════════════════════════════════════════════════════

RAIN_HEIGHT = 9               # How many rows at top stay as rain (taller = more rain)
_io_lock    = threading.Lock()  # Protects ALL stdout writes
_rain_stop  = threading.Event()  # Signal thread to quit


def generate_rain_line(width):
    """One row of random rain/bubble characters"""
    rain_chars   = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*!?><^~+-=")
    bubble_chars = list("○◎●◉◯⊙★☆◆◇▲△♦✦✧")
    stream_chars = list("│╎╏║|")
    rain_palette = [AQUA, LIME, PINK, GOLD, SKY, CYAN, GREEN, MAGEN]

    chars = []
    for _ in range(width):
        r = random.random()
        if r < 0.07:
            chars.append(BOLD + LIME + random.choice(stream_chars))
        elif r < 0.15:
            chars.append(BOLD + random.choice(rain_palette) + random.choice(rain_chars))
        elif r < 0.22:
            chars.append(AQUA + random.choice(bubble_chars))
        elif r < 0.32:
            chars.append(DIM + '\033[38;5;30m' + random.choice(rain_chars))
        else:
            chars.append(' ')
    return ''.join(chars) + R


def show_rain_animation():
    """One-time intro: full-screen scrolling rain"""
    width = min(shutil.get_terminal_size((80, 24)).columns, 110)
    sys.stdout.write('\033[2J\033[H')
    sys.stdout.flush()
    for _ in range(28):
        sys.stdout.write(generate_rain_line(width) + '\n')
        sys.stdout.flush()
        time.sleep(0.05)


def show_banner():
    """Startup banner (shown once after intro rain)"""
    W   = 66
    bar = '═' * (W - 2)

    def row(text, color=WHITE, bold=True):
        padded = text.center(W - 2)
        b = BOLD if bold else ''
        return f"{BOLD}{AQUA}║{R}{b}{color}{padded}{R}{BOLD}{AQUA}║{R}"

    def divider():
        return f"{BOLD}{AQUA}║{DIM}{CYAN}{'─' * (W - 2)}{R}{BOLD}{AQUA}║{R}"

    lines = [
        f"\n{BOLD}{AQUA}╔{bar}╗{R}",
        row(""),
        row("A S I F  T E C H  —  Y T  L I V E  B O T", CYAN),
        row("v 3 . 0  U L T R A  E D I T I O N", AQUA),
        row(""),
        divider(),
        row(""),
        row("[ AUTO-RESTART ]  [ ANTI-BAN ]  [ MULTI-TAB ]", GREEN),
        row("YouTube Live Chat Automation System", YELLOW),
        row(""),
        divider(),
        row(""),
        row("Config: config.json  |  URLs: urls.txt", MAGEN),
        row("Messages: messages.txt  |  Log: send_log.txt", MAGEN),
        row(""),
        f"{BOLD}{AQUA}╚{bar}╝{R}\n",
    ]
    for line in lines:
        print(line)
        time.sleep(0.03)


def init_rain_zone():
    """Clear screen, draw top rain section, lock it with scroll region"""
    term  = shutil.get_terminal_size((80, 24))
    width = min(term.columns, 110)
    rows  = term.lines

    with _io_lock:
        sys.stdout.write('\033[2J\033[H')          # Clear + home
        for _ in range(RAIN_HEIGHT):
            sys.stdout.write(generate_rain_line(width) + '\n')
        # Dim separator line between rain and logs
        sys.stdout.write(DIM + '\033[38;5;240m' + '─' * min(term.columns, 110) + R + '\n')
        # Set terminal scroll region: lines below rain+separator scroll, top stays fixed
        sys.stdout.write(f'\033[{RAIN_HEIGHT + 2};{rows}r')
        # Move cursor to top of log area
        sys.stdout.write(f'\033[{RAIN_HEIGHT + 2};1H')
        sys.stdout.flush()


def rain_updater_thread():
    """
    Live rain engine — runs for entire session:
    - Column-based falling drops (bright head → fading trail)
    - Bubble columns float independently
    - Color palette rotates automatically (cyan→green→magenta→gold→...)
    - Unlimited drops reset when they exit bottom
    - ~12 FPS continuous update
    """
    MATRIX  = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*!?><^~+-=")
    BUBBLES = list("○◎●◉◯⊙★☆◆◇▲△♦✦✧")
    STREAMS = list("│╎╏║|")

    # Palettes that cycle one-by-one (each lasts ~6.4 s at 80 frames each)
    PALETTES = [
        [AQUA,  SKY,    CYAN,   BLUE],
        [LIME,  GREEN,  '\033[38;5;40m',  '\033[38;5;35m'],
        [PINK,  MAGEN,  '\033[38;5;177m', '\033[38;5;171m'],
        [GOLD,  YELLOW, '\033[38;5;214m', '\033[38;5;208m'],
        [AQUA,  LIME,   PINK,   GOLD],
        [SKY,   LIME,   MAGEN,  CYAN],
    ]

    col_phase = {}   # col -> float (drop head row position)
    col_speed = {}   # col -> float (rows advanced per frame)
    col_type  = {}   # col -> 'matrix' | 'bubble' | 'stream'

    def reset_col(col):
        col_phase[col] = random.uniform(-RAIN_HEIGHT * 1.2, 0)
        col_speed[col] = random.uniform(0.10, 0.38)
        col_type[col]  = random.choices(
            ['matrix', 'bubble', 'stream'],
            weights=[60, 28, 12]
        )[0]

    pal_idx   = 0
    pal_frame = 0

    while not _rain_stop.is_set():
        term  = shutil.get_terminal_size((80, 24))
        width = min(term.columns, 110)

        # Slowly cycle color palette
        pal_frame += 1
        if pal_frame >= 80:
            pal_frame = 0
            pal_idx   = (pal_idx + 1) % len(PALETTES)
        pal = PALETTES[pal_idx]

        # Advance every column's drop
        for col in range(width):
            if col not in col_phase:
                reset_col(col)
            col_phase[col] += col_speed[col]
            if col_phase[col] > RAIN_HEIGHT + 5:
                reset_col(col)

        # Build full canvas for all RAIN_HEIGHT rows
        canvas = [[' '] * width for _ in range(RAIN_HEIGHT)]

        for col in range(width):
            phase    = col_phase[col]
            ctype    = col_type[col]
            chars    = BUBBLES if ctype == 'bubble' else (STREAMS if ctype == 'stream' else MATRIX)

            for row in range(RAIN_HEIGHT):
                dist = phase - row   # 0 = head is exactly here; +ve = this row is in the trail

                if dist < 0:
                    canvas[row][col] = ' '                                              # Not yet
                elif dist < 0.7:
                    canvas[row][col] = f"{BOLD}{WHITE}{random.choice(chars)}{R}"       # Bright head
                elif dist < 1.8:
                    canvas[row][col] = f"{BOLD}{pal[0]}{random.choice(chars)}{R}"      # Hot near-head
                elif dist < 3.2:
                    canvas[row][col] = f"{pal[1 % len(pal)]}{random.choice(chars)}{R}"# Mid trail
                elif dist < 5.0:
                    canvas[row][col] = f"{DIM}{pal[-1]}{random.choice(MATRIX)}{R}"    # Fading tail
                else:
                    canvas[row][col] = ' '                                              # Tail ended

        # Write entire canvas in one atomic stdout burst
        out = ['\033[s']                              # Save cursor once
        for row_idx in range(RAIN_HEIGHT):
            out.append(f'\033[{row_idx + 1};1H')      # Jump to row
            out.append('\033[2K')                     # Clear line
            out.append(''.join(canvas[row_idx]))
        out.append('\033[u')                          # Restore cursor once

        with _io_lock:
            sys.stdout.write(''.join(out))
            sys.stdout.flush()

        time.sleep(0.08)   # ~12 FPS


# ══════════════════════════════════════════════════════════════════════════════
#  COLORED LOGGER
# ══════════════════════════════════════════════════════════════════════════════

class ColoredFormatter(logging.Formatter):
    _FMT = "%(asctime)s  %(levelname)s  %(message)s"
    _COLORS = {
        logging.DEBUG:    DIM + WHITE,
        logging.INFO:     BOLD + CYAN,
        logging.WARNING:  BOLD + YELLOW,
        logging.ERROR:    BOLD + RED,
        logging.CRITICAL: BOLD + RED,
    }

    def format(self, record):
        color = self._COLORS.get(record.levelno, R)
        orig  = record.levelname
        record.levelname = f"{color}[{record.levelname:8}]{R}"
        result = logging.Formatter(self._FMT, datefmt="%H:%M:%S").format(record)
        record.levelname = orig
        return result


class LockedStreamHandler(logging.StreamHandler):
    """Console handler that syncs with the live rain thread via _io_lock"""
    def emit(self, record):
        with _io_lock:
            try:
                msg = self.format(record)
                self.stream.write(msg + self.terminator)
                self.stream.flush()
            except Exception:
                self.handleError(record)


def tprint(text):
    """Thread-safe print (for crash/restart messages in main)"""
    with _io_lock:
        sys.stdout.write(str(text) + '\n')
        sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def repair_invalid_config_text(raw_text):
    """Repair common JSON mistakes such as trailing commas before parsing."""
    if not raw_text or not raw_text.strip():
        return json.dumps(DEFAULT_CONFIG, indent=4)

    cleaned = raw_text
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    cleaned = re.sub(r'(?<=\d)\s+,\s*(?=["\d\[{])', ', ', cleaned)
    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        return json.dumps(DEFAULT_CONFIG, indent=4)


def load_live_config(logger=None):
    if not os.path.exists(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            raw = f.read()
        repaired = repair_invalid_config_text(raw)
        if repaired != raw:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(repaired)
        return json.loads(repaired)
    except Exception as e:
        if logger:
            logger.warning(f"config.json read failed: {e} — using defaults")
        return DEFAULT_CONFIG.copy()


def get_data(filename):
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        values = [line.strip() for line in f if line.strip()]
        return list(dict.fromkeys(values))


def acquire_single_instance(logger):
    """Allow only one bot process so manual start and Task Scheduler cannot overlap"""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "AsifTechGlobal_YT_Bot")
    if not mutex:
        return None
    if ctypes.windll.kernel32.GetLastError() == 183:
        logger.warning("Bot is already running; this duplicate instance will exit.")
        ctypes.windll.kernel32.CloseHandle(mutex)
        return None
    return mutex


def setup_logger(log_file):
    logger = logging.getLogger("yt_bot")
    logger.setLevel(logging.INFO)
    if logger.hasHandlers():
        logger.handlers.clear()
    # File handler — plain text
    fh = logging.FileHandler(os.path.join(BASE_DIR, log_file), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(fh)
    # Console handler — colored + thread-safe (won't interfere with rain)
    ch = LockedStreamHandler(sys.stdout)
    ch.setFormatter(ColoredFormatter())
    logger.addHandler(ch)
    return logger


def choose_message(messages, sent_history, allow_duplicates):
    if not messages:
        return None
    candidates = messages if allow_duplicates else [m for m in messages if m not in sent_history]
    if not candidates:
        sent_history.clear()
        candidates = messages
    return random.choice(candidates) if candidates else None


def cleanup_chrome_locks(profile_path):
    """Delete stale Chrome lock files so profile can be reused after a crash"""
    for lf in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        fp = os.path.join(profile_path, lf)
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass


def emulate_human_behavior(driver, config, logger):
    try:
        anti_ban = config.get("ANTI_BAN_SETTINGS", {})
        if anti_ban.get("MOUSE_MOVE_EMULATION", True):
            ActionChains(driver).move_by_offset(
                random.randint(10, 50), random.randint(10, 50)
            ).perform()
            time.sleep(0.5)
        if anti_ban.get("HUMAN_SCROLL", True):
            driver.execute_script(f"window.scrollBy(0, {random.randint(100, 300)});")
            time.sleep(1)
            driver.execute_script(f"window.scrollBy(0, -{random.randint(50, 150)});")
    except Exception:
        pass


def safe_send_text(chat_input, text, driver, logger):
    try:
        chat_input.click()
        time.sleep(0.5)
        chat_input.send_keys(Keys.CONTROL, "a")
        chat_input.send_keys(Keys.BACKSPACE)
        time.sleep(0.5)
        driver.execute_script(
            "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);",
            chat_input, text
        )
        time.sleep(1)
        chat_input.send_keys(Keys.ENTER)
        return True
    except Exception as e:
        logger.error(f"Send failed: {e}")
        return False


def is_live_chat_ready(driver, logger=None):
    try:
        driver.switch_to.default_content()
        frames = driver.find_elements(By.CSS_SELECTOR, "iframe#chatframe, iframe[src*='live_chat']")
        if frames:
            driver.switch_to.frame(frames[0])
            inputs = driver.find_elements(By.CSS_SELECTOR, "div#input, div[contenteditable='true']")
            return bool([i for i in inputs if i.is_displayed()])
    except Exception:
        pass
    return False


def is_stream_ended(driver, logger=None):
    """Detect if the live stream has finished (offline/ended), so its tab can be auto-closed"""
    try:
        page_text = driver.execute_script(
            "return document.body ? document.body.innerText : '';"
        ) or ""
        ended_markers = (
            "was live", "stream ended", "chat is disabled", "premiere in",
            "live chat replay", "this live stream recording is not available",
        )
        low = page_text.lower()
        if any(marker in low for marker in ended_markers):
            return True
    except Exception:
        pass
    return False


def resume_video(driver):
    """Resume YouTube video after automated navigation when Chrome pauses it."""
    try:
        driver.execute_script(
            """
            const video = document.querySelector('video');
            if (video && video.paused) {
                video.play().catch(() => {});
            }
            """
        )
    except Exception:
        pass


def remove_url_from_file(filename, url, base_dir):
    """Rewrite the tracked-urls file without the given url (auto-cleanup when a live ends)"""
    path = os.path.join(base_dir, filename)
    try:
        remaining = [u for u in get_data(filename) if u != url]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(remaining) + ("\n" if remaining else ""))
    except Exception:
        pass


def find_chat_input(driver, logger=None):
    for sel in (
        "div#input.yt-live-chat-text-input-field-renderer",
        "div#input",
        "div[contenteditable='true']",
        "textarea",
    ):
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, sel):
                if el.is_displayed():
                    return el
        except Exception:
            continue
    return None


def get_driver(options, logger):
    """Start ChromeDriver with a quick retry for transient startup failures."""
    cached_drivers = glob.glob(
        os.path.join(os.path.expanduser("~"), ".wdm", "drivers", "chromedriver", "**", "chromedriver.exe"),
        recursive=True,
    )
    driver_path = max(cached_drivers, key=os.path.getmtime) if cached_drivers else None
    if not driver_path:
        try:
            driver_path = ChromeDriverManager().install()
        except Exception as e:
            logger.warning(f"ChromeDriver lookup failed: {e}")

    for attempt in range(1, 3):
        try:
            service = Service(driver_path) if driver_path else Service()
            if os.name == "nt":
                service.creation_flags = 0x08000000
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.warning(f"ChromeDriver attempt {attempt}/2 failed: {e}")
            if attempt < 2:
                time.sleep(1)
    raise RuntimeError("Could not start ChromeDriver after 2 attempts")


# ══════════════════════════════════════════════════════════════════════════════
#  CORE BOT
# ══════════════════════════════════════════════════════════════════════════════

def start_bot():
    logger = setup_logger("send_log.txt")

    tracked_urls = get_data("urls.txt")
    if not tracked_urls:
        logger.error("urls.txt is empty — add YouTube live stream URLs first.")
        return

    live_config  = load_live_config(logger)
    sys_settings = live_config.get("SYSTEM_SETTINGS", DEFAULT_CONFIG["SYSTEM_SETTINGS"])
    profile_path = os.path.join(BASE_DIR, "Saved_YT_Session")

    cleanup_chrome_locks(profile_path)

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")

    if sys_settings.get("HEADLESS_MODE", False):
        options.add_argument("--headless=new")
        logger.info("Headless Mode ON — running in background.")

    logger.info("Starting Chrome...")
    driver = get_driver(options, logger)

    # Remove navigator.webdriver fingerprint
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    sent_history = set()
    active_tabs  = {}
    dead_counts  = {}   # url -> consecutive rounds where live chat wasn't found
    ENDED_THRESHOLD = 6  # after this many misses in a row, treat the stream as ended

    try:
        max_tabs     = live_config.get("MAX_TABS", 10)
        urls_to_open = tracked_urls[:max_tabs]

        logger.info(f"Opening {len(urls_to_open)} URL(s)...")
        driver.get(urls_to_open[0])
        active_tabs[urls_to_open[0]] = driver.current_window_handle
        time.sleep(3)
        resume_video(driver)

        for url in urls_to_open[1:]:
            driver.execute_script("window.open(arguments[0], '_blank');", url)
            time.sleep(1)
            try:
                new_handle = next(h for h in driver.window_handles if h not in active_tabs.values())
                active_tabs[url] = new_handle
            except StopIteration:
                logger.warning(f"Could not get handle for: {url}")

        # ── MAIN LOOP ──────────────────────────────────────────────────────────
        while True:
            current_urls = get_data("urls.txt")
            live_config  = load_live_config(logger)
            max_tabs     = live_config.get("MAX_TABS", 10)

            # Close tabs whose URLs were removed from file
            for url in list(active_tabs):
                if url not in current_urls:
                    logger.info(f"Closing removed URL tab: {url}")
                    try:
                        driver.switch_to.window(active_tabs[url])
                        driver.close()
                    except Exception:
                        pass
                    del active_tabs[url]
                    dead_counts.pop(url, None)
                    time.sleep(0.5)

            # Open tabs for newly added URLs
            for url in current_urls:
                if url not in active_tabs and len(active_tabs) < max_tabs:
                    logger.info(f"New URL — opening tab: {url}")
                    driver.execute_script("window.open(arguments[0], '_blank');", url)
                    time.sleep(1)
                    try:
                        new_handle = next(h for h in driver.window_handles if h not in active_tabs.values())
                        active_tabs[url] = new_handle
                    except StopIteration:
                        pass

            if not active_tabs:
                logger.warning("No active tabs — waiting 10s...")
                time.sleep(10)
                continue

            # Process each tab
            for idx, (url, tab_handle) in enumerate(list(active_tabs.items())):
                live_config   = load_live_config(logger)
                loop_settings = live_config.get("LOOP_SETTINGS", {})

                logger.info(f"Tab [{idx + 1}/{len(active_tabs)}] Processing...")
                try:
                    driver.switch_to.window(tab_handle)
                except Exception:
                    active_tabs.pop(url, None)
                    continue

                time.sleep(2)
                resume_video(driver)
                emulate_human_behavior(driver, live_config, logger)

                messages = get_data("messages.txt")
                if not messages:
                    logger.warning("messages.txt is empty — add some comments!")
                    time.sleep(5)
                    continue

                if is_live_chat_ready(driver, logger):
                    dead_counts[url] = 0
                    msg = choose_message(
                        messages, sent_history,
                        loop_settings.get("ALLOW_DUPLICATE_MESSAGES", False)
                    )
                    if msg:
                        chat_box = find_chat_input(driver, logger)
                        if chat_box:
                            if safe_send_text(chat_box, msg, driver, logger):
                                logger.info(f"Sent on Tab {idx + 1}: {msg}")
                                sent_history.add(msg)
                                # ── Credit check ──────────────────────────
                                ok, credit_msg = _use_credit_api()
                                if not ok:
                                    logger.warning("=" * 55)
                                    logger.warning("FREE LIMIT KHATAM!")
                                    logger.warning(credit_msg or "Rs.20 mein 20 din unlimited upgrade karo.")
                                    logger.warning("http://localhost:5000/upgrade")
                                    logger.warning("=" * 55)
                                    return   # stop bot gracefully
                else:
                    logger.warning(f"Live chat not ready on Tab {idx + 1}")
                    if is_stream_ended(driver, logger):
                        dead_counts[url] = ENDED_THRESHOLD
                    else:
                        dead_counts[url] = dead_counts.get(url, 0) + 1

                    if dead_counts.get(url, 0) >= ENDED_THRESHOLD:
                        logger.info(f"Live ended — auto-closing & removing: {url}")
                        try:
                            driver.close()
                        except Exception:
                            pass
                        active_tabs.pop(url, None)
                        dead_counts.pop(url, None)
                        remove_url_from_file("urls.txt", url, BASE_DIR)
                        if driver.window_handles:
                            driver.switch_to.window(driver.window_handles[0])
                        continue

                driver.switch_to.default_content()

                delay = (
                    random.randint(
                        live_config.get("MIN_DELAY", 10),
                        live_config.get("MAX_DELAY", 25),
                    )
                    if live_config.get("RANDOM_DELAY", True)
                    else live_config.get("INTERVAL", 15)
                )
                logger.info(f"Waiting {delay}s...")
                time.sleep(delay)

            batch_delay = live_config.get("LOOP_SETTINGS", {}).get("BATCH_SLEEP_DELAY", 30)
            logger.info(f"Round done | Active tabs: {len(active_tabs)} | Sleeping {batch_delay}s...")
            time.sleep(batch_delay)

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
        raise
    finally:
        try:
            driver.quit()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-RESTART WRAPPER
# ══════════════════════════════════════════════════════════════════════════════

def main():
    logger = setup_logger("send_log.txt")
    if acquire_single_instance(logger) is None:
        return 2

    # ── Step 1: lightweight startup display ───────────────────────────────────
    show_banner()

    # ── Step 2: set up fixed rain zone + scroll region for logs ───────────────
    init_rain_zone()

    # ── Step 3: start background rain thread ──────────────────────────────────
    rain_thread = threading.Thread(target=rain_updater_thread, daemon=True)
    rain_thread.start()

    # ── Step 4: auto-restart bot loop until the user stops it ───────────────
    attempt = 0
    try:
        while True:
            attempt += 1
            try:
                start_bot()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                wait = min(60, 10 * attempt)
                tprint(f"\n{BOLD}{RED}  [CRASH #{attempt}] {e}{R}")
                tprint(f"{BOLD}{YELLOW}  Auto-restarting in {wait}s...{R}\n")
                time.sleep(wait)
    except KeyboardInterrupt:
        pass
    finally:
        # ── Cleanup ───────────────────────────────────────────────────────────
        _rain_stop.set()
        with _io_lock:
            sys.stdout.write('\033[r')      # Reset scroll region to full screen
            sys.stdout.write('\033[?25h')   # Ensure cursor is visible
            sys.stdout.flush()
        tprint(f"\n{BOLD}{RED}  Stopped. Bye!{R}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)