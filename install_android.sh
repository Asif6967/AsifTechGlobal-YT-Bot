#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════
#   AsifTechGlobal — Android Auto Installer
#   Run this ONE command in Termux:
#   curl -sL https://files.catbox.moe/SCRIPT_URL | bash
# ═══════════════════════════════════════════════

clear
echo ""
echo "╔══════════════════════════════════════╗"
echo "║    AsifTechGlobal Android Setup     ║"
echo "║    Please wait...                   ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Step 1: Storage permission
echo "[1/4] Storage permission..."
termux-setup-storage 2>/dev/null
sleep 2

# Step 2: Install system packages
echo "[2/4] Python install ho raha hai..."
pkg install -y python python-pip wget unzip 2>&1 | grep -E "already|installed|error" | tail -3

# Step 3: Install Python packages
echo "[3/4] Bot libraries install ho rahi hain..."
pip install flask flask-login werkzeug authlib joserfc requests -q --no-warn-script-location

# Step 4: Download bot
echo "[4/4] Bot download ho raha hai..."
wget -q "https://files.catbox.moe/7yt5x1.zip" -O ~/atg_bot.zip
mkdir -p ~/AsifTechGlobal
unzip -q ~/atg_bot.zip -d ~/AsifTechGlobal 2>/dev/null
rm ~/atg_bot.zip 2>/dev/null

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       ✓ Setup Complete!             ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Bot start ho raha hai..."
echo "  Browser mein kholo: http://localhost:5000"
echo ""

# Auto start
cd ~/AsifTechGlobal
python termux_app.py
