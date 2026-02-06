#!/bin/bash
set -e

REMOTE_USER="ubuntu"
REMOTE_HOST="57.128.242.21"
REMOTE_DIR="/home/ubuntu/gmud"
SERVICE_NAME="gmud"

# ---------------------------
# 1. Sync all files (including .env)
# ---------------------------
echo "📤 Syncing project files..."
rsync -avz --exclude ".env" --exclude "gmud_data.json" --exclude ".git" --exclude "venv" --exclude "__pycache__" ./ $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR

# ---------------------------
# 2. Install Python dependencies system-wide + Firefox + geckodriver
# ---------------------------
ssh $REMOTE_USER@$REMOTE_HOST << 'ENDSSH'
set -e
cd ~/gmud

sudo apt update
sudo apt install -y python3-pip python3-httpx python3-requests python3-dotenv python3-dateutil wget bzip2 ca-certificates

pip3 install --break-system-packages aiogram selenium

# ---- Install Firefox non-snap ----
if command -v snap >/dev/null 2>&1 && snap list 2>/dev/null | grep -q firefox; then
  sudo snap remove firefox
fi

if ! command -v firefox >/dev/null 2>&1 || firefox --version | grep -q snap; then
  cd /opt
  sudo wget -q -O firefox.tar.bz2 "https://ftp.mozilla.org/pub/firefox/releases/latest/linux-x86_64/en-US/firefox-111.0.tar.bz2"
  sudo tar -xjf firefox.tar.bz2
  sudo rm firefox.tar.bz2
  sudo ln -sf /opt/firefox/firefox /usr/local/bin/firefox
fi

# ---- Install geckodriver ----
if ! command -v geckodriver >/dev/null 2>&1; then
  GECKO_VERSION="v0.35.0"
  wget -q https://github.com/mozilla/geckodriver/releases/download/$GECKO_VERSION/geckodriver-$GECKO_VERSION-linux64.tar.gz
  tar -xzf geckodriver-$GECKO_VERSION-linux64.tar.gz
  sudo mv geckodriver /usr/local/bin/
  sudo chmod +x /usr/local/bin/geckodriver
  rm geckodriver-$GECKO_VERSION-linux64.tar.gz
fi
# ---------------------------------------

ENDSSH

# ---------------------------
# 3. Install systemd service
# ---------------------------
ssh $REMOTE_USER@$REMOTE_HOST << 'ENDSSH'
set -e
sudo cp ~/gmud/gmud.service /etc/systemd/system/gmud.service
sudo systemctl daemon-reload
sudo systemctl enable gmud
sudo systemctl restart gmud
ENDSSH

echo "✅ Deployment complete!"
echo "📖 Follow logs: ssh $REMOTE_USER@$REMOTE_HOST 'sudo journalctl -u gmud -f'"
