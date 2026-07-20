# CRUD Master

## Overview
Movie streaming platform microservices project:
- **Inventory API** — CRUD API for movies, backed by PostgreSQL (`movies_db`).
- **Billing API** — Async order processor consuming from RabbitMQ (`billing_queue`), backed by PostgreSQL (`billing_db`).
- **API Gateway** — Single entry point routing to Inventory (HTTP) and Billing (RabbitMQ).

## Stack
- Python 3, Flask, SQLAlchemy
- PostgreSQL
- RabbitMQ (pika)
- Vagrant + VirtualBox
- PM2

## Architecture
_(fill in diagram / description — see resources/crud-master-diagram.png)_

## Environment Variables
See `.env`. Required variables:
- `INVENTORY_DB_*` — Postgres credentials for movies_db
- `BILLING_DB_*` — Postgres credentials for billing_db
- `RABBITMQ_*` — RabbitMQ connection details
- `INVENTORY_API_URL`, `INVENTORY_API_PORT`
- `GATEWAY_PORT`

## Setup & Run (local, pre-VM)
```bash
# Inventory API
cd srcs/inventory-app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py

# Billing API
cd srcs/billing-app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py

# API Gateway
cd srcs/api-gateway-app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py
```

## Setup & Run (Vagrant)
```bash
vagrant up
vagrant status
vagrant ssh <vm-name>
```

## Testing
- Postman collection: `docs/postman_collection.json` (export after building tests)
- OpenAPI spec: `docs/openapi.yaml`

## Design Choices
_(document decisions here — why Flask, why this file structure, etc.)_
