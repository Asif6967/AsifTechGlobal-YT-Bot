#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════
#   AsifTechGlobal — Android Termux Setup Script
#   Run: bash termux_setup.sh
# ═══════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   AsifTechGlobal — Android Setup        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ─── Step 1: Update packages ──────────────────────────
echo "[1/5] Packages update ho raha hai..."
pkg update -y -q 2>&1 | tail -2

# ─── Step 2: Install Python ───────────────────────────
echo "[2/5] Python install ho raha hai..."
pkg install -y python python-pip libffi openssl 2>&1 | tail -2

# ─── Step 3: Upgrade pip ──────────────────────────────
echo "[3/5] pip upgrade ho raha hai..."
pip install --upgrade pip -q

# ─── Step 4: Install Python packages ─────────────────
echo "[4/5] Python packages install ho rahe hain..."
pip install \
    flask \
    flask-login \
    werkzeug \
    authlib \
    joserfc \
    requests \
    -q

# ─── Step 5: Done ─────────────────────────────────────
echo "[5/5] Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  BOT CHALANE KA TARIKA:"
echo ""
echo "  STEP 1 — Bot start karo:"
echo "    python termux_app.py"
echo ""
echo "  STEP 2 — Browser mein kholo:"
echo "    http://localhost:5000"
echo ""
echo "  STEP 3 — YouTube Cookies set karo:"
echo "    Panel → Settings → YouTube Cookies"
echo ""
echo "  COOKIES KAISE LEIN (Android Firefox):"
echo "    1. Firefox install karo (Play Store)"
echo "    2. youtube.com kholain, login karo"
echo "    3. Address bar mein: about:addons"
echo "    4. 'Cookie Editor' extension install karo"
echo "    5. YouTube.com pe jao"
echo "    6. Cookie Editor icon → Export → Header String"
echo "    7. Copy karo → Panel mein paste karo → Save"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FILES BANAO (Termux mein):"
echo "    mkdir -p ~/AsifTechGlobal"
echo "    echo 'https://youtube.com/watch?v=VIDEO_ID' > ~/AsifTechGlobal/urls.txt"
echo "    echo 'Hello!' > ~/AsifTechGlobal/messages.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


# ─── Step 5: Done ─────────────────────────────────────
echo "[5/5] Setup complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AB KYA KARNA HAI:"
echo ""
echo "  STEP 1 — YouTube API Credentials banao:"
echo "    1. Apne phone ke browser mein kholo:"
echo "       https://console.cloud.google.com"
echo "    2. New Project banao (koi bhi naam)"
echo "    3. APIs & Services > Library mein jao"
echo "    4. 'YouTube Data API v3' search karo > Enable karo"
echo "    5. Credentials > + Create Credentials"
echo "       > OAuth Client ID > Desktop App > Create"
echo "    6. JSON download karo"
echo "    7. File ka naam rakho: yt_credentials.json"
echo "    8. Is folder mein rakho (copy/move karo):"
echo "       ~/AsifTechGlobal/yt_credentials.json"
echo ""
echo "  STEP 2 — Bot start karo:"
echo "    python termux_app.py"
echo ""
echo "  STEP 3 — Login hoga (pehli baar):"
echo "    Terminal mein ek URL dikhega"
echo "    Us URL ko apne mobile browser mein kholo"
echo "    Google se login karo > Code copy karo"
echo "    Terminal mein code paste karo > Enter"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  FAILE BANAO (Termux mein):"
echo "    mkdir -p ~/AsifTechGlobal"
echo "    echo 'https://youtube.com/watch?v=VIDEO_ID' > ~/AsifTechGlobal/urls.txt"
echo "    echo 'Hello!' > ~/AsifTechGlobal/messages.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
