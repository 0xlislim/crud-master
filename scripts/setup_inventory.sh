#!/usr/bin/env bash
set -e

echo "=== Provisioning inventory-vm ==="

# --- System packages ---
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip postgresql postgresql-contrib curl

# --- Node.js + PM2 (PM2 requires Node.js even though our apps are Python) ---
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
sudo npm install -g pm2

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${INVENTORY_DB_NAME:-movies_db}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE ${INVENTORY_DB_NAME:-movies_db} OWNER ${INVENTORY_DB_USER:-inventory_user};"

# --- Create movies table (idempotent, safe to re-run) ---
sudo -u postgres psql -d "${INVENTORY_DB_NAME:-movies_db}" -f /vagrant/scripts/init_movies_db.sql

# --- App setup ---
APP_DIR="/vagrant/srcs/inventory-app"
cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# --- Start with PM2 ---
sudo pm2 delete inventory-app 2>/dev/null || true
sudo pm2 start "$APP_DIR/venv/bin/python" --name inventory-app -- "$APP_DIR/server.py"
sudo pm2 save

# --- Ensure PM2 resurrects this process list automatically on VM reboot ---
sudo pm2 startup systemd -u root --hp /root | tail -1 | bash || true

echo "=== inventory-vm provisioning complete ==="