# ⚡ AsifTechGlobal — YT Bot Panel

> YouTube Live Chat Automation Platform — Ultra Premium

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-Web%20Panel-green?style=flat-square&logo=flask)
![Platform](https://img.shields.io/badge/Platform-PC%20%7C%20Mobile%20%7C%20iPhone-gold?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## 🚀 Features

- **Multi-user** web panel with Google/Facebook/Email login
- **YouTube Live Chat** automation — auto send messages
- **Free Plan** — 1200 comments demo
- **Paid Plan** — ₹20 = 20 days unlimited
- **Mobile support** — works on Android (Termux) + iPhone + PC
- **Ultra Premium UI** — AsifTechGlobal brand design
- **Admin panel** — manage users, generate activation keys
- **Push notifications** — browser alerts on bot events
- **Anti-ban** — human scroll, mouse emulation, random delays

---

## 📦 Installation

### PC (Windows / Linux / Mac)

```bash
# 1. Clone repo
git clone https://github.com/YOUR_USERNAME/yt-bot-panel.git
cd yt-bot-panel

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python web_panel.py
```

Open browser: `http://localhost:5000`

---

### 📱 Android (Termux)

```bash
# 1. Install Termux from F-Droid
# 2. Run setup
termux-setup-storage
pkg install python git
git clone https://github.com/YOUR_USERNAME/yt-bot-panel.git
cd yt-bot-panel
bash termux_setup.sh
python termux_app.py
```

---

## 🌐 Access from Mobile

Same WiFi pe phone se access karo:
```
http://YOUR_PC_IP:5000
```

---

## 💰 Plans

| Plan | Price | Comments | Duration |
|------|-------|----------|----------|
| Free | ₹0 | 1,200 | Lifetime |
| Paid | ₹20 | Unlimited | 20 days |

---

## ⚙️ Config

Copy `config.json.example` to `config.json` and edit:

```json
{
  "PLATFORM": "youtube",
  "INTERVAL": 15,
  "MAX_TABS": 5,
  "SPEED_MODE": "normal"
}
```

---

## 🔐 Admin Panel

```
http://localhost:5000/admin?key=YOUR_ADMIN_KEY
```

Set your admin key via environment variable:
```bash
set ATG_ADMIN_KEY=your_secret_key
python web_panel.py
```

---

## 📋 Requirements

```
flask
flask-login
werkzeug
authlib
selenium
webdriver-manager
requests
```

---

## 🛡️ Security Notes

- Never commit `oauth_config.json`, `.secret_key`, or `users.db`
- Change `ATG_ADMIN_KEY` before deploying
- Use HTTPS in production (behind nginx)

---

## 📱 Deploy Free (24/7)

Best free hosting options:

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| **Railway** | 500 hrs/mo | Easy deploy |
| **Render** | 750 hrs/mo | Free PostgreSQL |
| **Koyeb** | Always free | Good for Flask |

---

## 🧑‍💻 Made by

**AsifTechGlobal** — YouTube Automation Tools

---

## 📄 License

MIT License — Free to use and modify.
