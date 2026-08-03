// PM2 ecosystem config for the Inventory API.
// Binds on 0.0.0.0 so the gateway-vm can reach it (the shared .env uses
// "localhost", which would make the API loopback-only).
module.exports = {
  apps: [
    {
      name: "inventory-app",
      script: "/vagrant/srcs/inventory-app/server.py",
      interpreter: "/vagrant/srcs/inventory-app/venv/bin/python",
      cwd: "/vagrant/srcs/inventory-app",
      env: {
        INVENTORY_API_HOST: "0.0.0.0"
      }
    }
  ]
};
