// PM2 ecosystem config for the API Gateway.
// Sets the cross-VM addresses (the shared .env uses "localhost" for local dev).
// The gateway reaches the Inventory API and RabbitMQ over the VM private network.
module.exports = {
  apps: [
    {
      name: "api-gateway-app",
      script: "/vagrant/srcs/api-gateway-app/server.py",
      interpreter: "/vagrant/srcs/api-gateway-app/venv/bin/python",
      cwd: "/vagrant/srcs/api-gateway-app",
      env: {
        INVENTORY_API_HOST: "192.168.56.11",
        RABBITMQ_HOST: "192.168.56.12"
      }
    }
  ]
};
