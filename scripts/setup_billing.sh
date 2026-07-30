#!/usr/bin/env bash
set -e

echo "=== Provisioning billing-vm ==="

# --- System packages ---
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip postgresql postgresql-contrib rabbitmq-server curl

# --- Node.js + PM2 ---
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
sudo npm install -g pm2

# --- Start RabbitMQ ---
sudo systemctl enable rabbitmq-server || sudo service rabbitmq-server start
sudo service rabbitmq-server start

# --- RabbitMQ user (idempotent) ---
if [ "${RABBITMQ_USER:-guest}" != "guest" ]; then
  sudo rabbitmqctl add_user "${RABBITMQ_USER}" "${RABBITMQ_PASSWORD}" 2>/dev/null || true
  sudo rabbitmqctl set_user_tags "${RABBITMQ_USER}" administrator
  sudo rabbitmqctl set_permissions -p / "${RABBITMQ_USER}" ".*" ".*" ".*"
fi

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${BILLING_DB_NAME:-billing_db}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE ${BILLING_DB_NAME:-billing_db} OWNER ${BILLING_DB_USER:-billing_user};"

# --- Create orders table (idempotent, safe to re-run) ---
sudo -u postgres psql -d "${BILLING_DB_NAME:-billing_db}" -f /vagrant/scripts/init_billing_db.sql

# --- App setup ---
APP_DIR="/vagrant/srcs/billing-app"
cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# --- Start with PM2 ---
sudo pm2 delete billing-app 2>/dev/null || true
sudo pm2 start "$APP_DIR/venv/bin/python" --name billing-app -- "$APP_DIR/server.py"
sudo pm2 save

# --- Ensure PM2 resurrects this process list automatically on VM reboot ---
sudo pm2 startup systemd -u root --hp /root | tail -1 | bash || true

echo "=== billing-vm provisioning complete ==="