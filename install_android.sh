#!/data/data/com.termux/files/usr/bin/bash
# One-command Android installer for the current public repository.

set -u
REPO_URL="https://github.com/Asif6967/AsifTechGlobal-YT-Bot.git"
APP_DIR="$HOME/AsifTechGlobal-YT-Bot"

pkg update -y
pkg install -y git python python-pip libffi openssl

if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi

if cd "$APP_DIR"; then
  bash termux_setup.sh
  printf '\nStarting the panel...\n'
  python termux_app.py
else
  echo "[ERROR] Could not open $APP_DIR"
fi
