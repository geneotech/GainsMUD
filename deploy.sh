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
# 2. Install Python dependencies system-wide
# ---------------------------
ssh $REMOTE_USER@$REMOTE_HOST << 'ENDSSH'
set -e
cd ~/gmud

sudo apt update
sudo apt install -y python3-pip
sudo apt install python3-httpx python3-requests python3-dotenv python3-dateutil
pip3 install --break-system-packages aiogram selenium

# Install Selenium and Firefox WebDriver for whale scraping
sudo apt install -y firefox wget

# ---- FIX: manual geckodriver install ----
if ! command -v geckodriver >/dev/null 2>&1; then
  wget https://github.com/mozilla/geckodriver/releases/download/v0.35.0/geckodriver-v0.35.0-linux64.tar.gz
  tar -xzf geckodriver-v0.35.0-linux64.tar.gz
  sudo mv geckodriver /usr/local/bin/
  sudo chmod +x /usr/local/bin/geckodriver
  rm geckodriver-v0.35.0-linux64.tar.gz
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
