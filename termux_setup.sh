#!/data/data/com.termux/files/usr/bin/bash
# AsifTechGlobal — Android / Termux dependency setup
# Run from the extracted project folder: bash termux_setup.sh

set -u

if [ ! -f termux_app.py ]; then
  echo "[ERROR] Run this script from the extracted AsifTechGlobal project folder."
  printf 'Example: cd ~/bot && bash termux_setup.sh\n'
else
  echo ""
  echo "[1/4] Updating Termux packages..."
  pkg update -y
  echo "[2/4] Installing Python..."
  pkg install -y python python-pip libffi openssl
  echo "[3/4] Installing panel dependencies..."
  python -m pip install --upgrade pip
  python -m pip install flask flask-login werkzeug authlib requests
  echo "[4/4] Setup complete."
  echo ""
  echo "Start the panel with: python termux_app.py"
  echo "Then open: http://localhost:5000"
  echo "Before starting the bot, save your own YouTube cookies in Panel > Settings and add a live URL."
fi
