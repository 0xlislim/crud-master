#!/usr/bin/env bash
set -e

echo "=== Provisioning gateway-vm ==="

# --- System packages ---
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip curl

# --- Node.js + PM2 ---
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
sudo npm install -g pm2

# --- App setup ---
APP_DIR="/vagrant/srcs/api-gateway-app"
cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# --- Start with PM2 ---
sudo pm2 delete api-gateway-app 2>/dev/null || true
sudo pm2 start "$APP_DIR/venv/bin/python" --name api-gateway-app -- "$APP_DIR/server.py"
sudo pm2 save

# --- Ensure PM2 resurrects this process list automatically on VM reboot ---
sudo pm2 startup systemd -u root --hp /root | tail -1 | bash || true

echo "=== gateway-vm provisioning complete ==="