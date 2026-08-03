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

# --- Cross-VM connectivity ---
# The gateway must reach the Inventory API and RabbitMQ on the other VMs.
# The shared .env uses "localhost"; the per-VM addresses are set in the PM2
# ecosystem config (env set by PM2 survives sudo, plain shell exports do not).
# See srcs/api-gateway-app/ecosystem.config.js.

# --- App setup ---
APP_DIR="/vagrant/srcs/api-gateway-app"
cd "$APP_DIR"
# The shared folder may carry a host-created venv with dangling symlinks;
# recreate it with the VM's Python.
rm -rf venv
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# --- Start with PM2 ---
sudo pm2 delete api-gateway-app 2>/dev/null || true
sudo pm2 start "$APP_DIR/ecosystem.config.js"
sudo pm2 save

# --- Ensure PM2 resurrects this process list automatically on VM reboot ---
sudo pm2 startup systemd -u root --hp /root | tail -1 | bash || true

echo "=== gateway-vm provisioning complete ==="