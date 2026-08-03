// PM2 ecosystem config for the Billing API (RabbitMQ consumer).
// No extra env needed: the shared .env already points at the local broker and
// billing_db, both of which live on billing-vm.
module.exports = {
  apps: [
    {
      name: "billing-app",
      script: "/vagrant/srcs/billing-app/server.py",
      interpreter: "/vagrant/srcs/billing-app/venv/bin/python",
      cwd: "/vagrant/srcs/billing-app"
    }
  ]
};
