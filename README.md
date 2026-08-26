# ⚡ AsifTechGlobal — YT Bot Panel

<div align="center">

![AsifTechGlobal](https://img.shields.io/badge/AsifTechGlobal-YT%20Bot-f0b429?style=for-the-badge&logo=youtube&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-green?style=for-the-badge&logo=flask)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)

**Ultra Premium YouTube Live Chat Automation Platform**

*Free: 1200 comments demo | Paid: ₹20 = 20 days unlimited*

</div>

---

## ✨ Features

- 🤖 **Auto comment** on YouTube Live streams
- 👥 **Multi-user** — each user gets their own isolated bot
- 🔐 **Auth** — Email/Password + Google + Facebook OAuth
- 📱 **Works everywhere** — PC, Mobile, iPhone, Android (Termux)
- ⚡ **Speed modes** — Slow / Normal / Fast / Turbo / Custom
- 💰 **Built-in monetization** — Free 1200 comments, then ₹20/20 days
- 🔑 **Activation key system** — Generate & send keys after payment
- 🛡️ **Anti-ban** — Human scroll, mouse emulation, random delays
- 📊 **Live logs** — Real-time SSE log stream
- 🔔 **Push notifications** — Browser notifications on bot events
- 🌐 **PWA** — Install as app on mobile

---

## 🚀 Quick Start

### 1. Clone
```bash
git clone https://github.com/Asif6967/AsifTechGlobal-YT-Bot.git
cd AsifTechGlobal-YT-Bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup config
```bash
# Copy example config
copy config.example.json config.json

# Optional: Setup Google/Facebook OAuth
copy oauth_config.example.json oauth_config.json
# Edit oauth_config.json with your credentials
```

### 4. Run
```bash
python web_panel.py
```

### 5. Open in browser
```
PC:     http://localhost:5000
Mobile: http://YOUR_PC_IP:5000
```

---

## 📱 Android / Termux Setup

1. Install **Termux** from F-Droid
2. Go to `http://YOUR_PC_IP:5000` on phone → Download Android Package
3. In Termux:
```bash
termux-setup-storage
cp /sdcard/Download/AsifTechGlobal_Android.zip ~/
cd ~/ && unzip AsifTechGlobal_Android.zip -d bot
cd bot && bash termux_setup.sh
python termux_app.py
```

---

## 💰 Monetization System

| Plan | Price | Limit |
|------|-------|-------|
| **Free** | ₹0 | 1200 comments (lifetime demo) |
| **Paid** | ₹20 | Unlimited for 20 days |

### How it works:
1. User hits 1200 comment limit → bot stops automatically
2. User goes to `/upgrade` page → pays ₹20 via UPI
3. User sends screenshot on WhatsApp
4. You verify → generate key from `/admin?key=YOUR_ADMIN_KEY`
5. User enters key → plan activates instantly

### Admin Panel
```
http://localhost:5000/admin?key=atgadmin2024
```
> ⚠️ Change `ADMIN_SECRET` in `web_panel.py` before deploying!

---

## ⚙️ Configuration

Edit `config.json` (copy from `config.example.json`):

| Setting | Description | Default |
|---------|-------------|---------|
| `MAX_TABS` | Parallel browser tabs | 5 |
| `INTERVAL` | Seconds between sends | 15 |
| `MIN_DELAY` | Min random delay (sec) | 3 |
| `MAX_DELAY` | Max random delay (sec) | 6 |
| `SPEED_MODE` | slow/normal/fast/turbo/custom | normal |
| `HEADLESS_MODE` | Run Chrome hidden | false |
| `HUMAN_SCROLL` | Anti-ban scroll | true |

---

## 🔐 Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web Application)
4. Add Authorized Redirect URIs:
   - `http://localhost:5000/auth/google/callback`
   - `http://YOUR_IP:5000/auth/google/callback`
5. Copy credentials to `oauth_config.json`

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask, Flask-Login, Authlib
- **Bot:** Selenium, WebDriver Manager
- **Database:** SQLite (users, activation keys)
- **Frontend:** Vanilla HTML/CSS/JS — no framework, ultra-premium design
- **Mobile:** PWA + Termux Android support

---

## 📁 Project Structure

```
AsifTechGlobal-YT-Bot/
├── web_panel.py          # Main Flask app + all API routes
├── bot.py                # Selenium bot (Chrome/desktop)
├── bot_mobile.py         # Cookie-based bot (mobile/headless)
├── bot_headless.py       # Headless variant
├── browser_utils.py      # Shared browser utilities
├── templates/
│   ├── login.html        # Ultra-premium login page
│   ├── index.html        # Main dashboard (5 pages)
│   ├── upgrade.html      # Payment/upgrade page
│   └── admin.html        # Admin panel
├── static/
│   ├── manifest.json     # PWA manifest
│   ├── sw.js             # Service worker
│   └── icon-192.png      # App icon
├── config.example.json   # Config template
├── oauth_config.example.json
└── requirements.txt
```

---

## ⚠️ Important Notes

- **Change admin password** before deploying: `ADMIN_SECRET` in `web_panel.py`
- **Never commit** `oauth_config.json`, `users.db`, `.secret_key`
- This tool is for **educational purposes** — use responsibly
- YouTube's Terms of Service prohibit automated interactions

---

## 👨‍💻 Author

**AsifTechGlobal** — [GitHub](https://github.com/Asif6967)

---

<div align="center">
⭐ Star this repo if it helped you!
</div>
