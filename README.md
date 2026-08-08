# CRUD Master

A movie streaming platform built as a microservices exercise: three Python
services, one PostgreSQL and one RabbitMQ per role, orchestrated with Vagrant
and kept alive with PM2.

## Overview

The platform is composed of three services:

- **Inventory API** — RESTful CRUD API for movies, backed by PostgreSQL
  (`movies_db`). Exposes `/api/movies` endpoints.
- **Billing API** — asynchronous order processor. Consumes JSON messages from
  RabbitMQ's `billing_queue`, inserts them into PostgreSQL (`billing_db.orders`)
  and acknowledges each message. It has **no HTTP endpoint** — it is driven
  exclusively by the message queue.
- **API Gateway** — the single entry point for clients. Routes `/api/movies`
  to the Inventory API over **HTTP**, and `POST /api/billing` to RabbitMQ's
  `billing_queue` (the Billing API picks it up asynchronously).

```
                    ┌──────────────────────────────┐
                    │        API Gateway           │
                    │      (port 9000)             │
                    └──────┬───────────────┬───────┘
                           │ HTTP          │ RabbitMQ
                           │               ▼
                ┌──────────▼────────┐   ┌──────────────────────────┐
                │  Inventory API    │   │      Billing API          │
                │  (port 8080)      │   │  (RabbitMQ consumer)      │
                └──────────┬────────┘   └────────────┬─────────────┘
                           │ SQLAlchemy              │ SQLAlchemy
                    ┌──────▼────────┐        ┌───────▼─────────────┐
                    │   movies_db   │        │      billing_db      │
                    │  (PostgreSQL) │        │   (PostgreSQL)       │
                    └───────────────┘        └─────────────────────┘

                    (RabbitMQ broker — billing_queue — sits between the
                     Gateway and the Billing API)
```

Three VMs, one service each:

- `gateway-vm` (192.168.56.10) — API Gateway only.
- `inventory-vm` (192.168.56.11) — Inventory API + `movies_db`.
- `billing-vm` (192.168.56.12) — Billing API + `billing_db` + RabbitMQ.

## Stack

- Python 3, Flask, SQLAlchemy, psycopg2
- PostgreSQL
- RabbitMQ (`pika`)
- Vagrant + VirtualBox
- PM2 (process manager / resilience testing)
- Postman (API testing)

## Project structure

```console
.
├── README.md
├── config.yaml
├── .env                       # committed per the exercise requirements
├── docs/
│   ├── openapi.yaml           # API Gateway OpenAPI/Swagger doc
│   ├── postman_collection.json# exported Postman tests
│   ├── billing-test-steps.md  # Billing resilience test scenarios
│   └── scrum-task-board.md    # sprint/backlog tracking
├── scripts/
│   ├── setup_gateway.sh       # provision gateway-vm
│   ├── setup_inventory.sh     # provision inventory-vm
│   ├── setup_billing.sh       # provision billing-vm
│   ├── init_movies_db.sql     # movies table
│   ├── init_billing_db.sql    # orders table
│   └── test_local.sh          # local integration smoke test
├── srcs/
│   ├── api-gateway-app/       # Flask app: proxy + RabbitMQ publisher
│   ├── billing-app/           # RabbitMQ consumer -> billing_db
│   └── inventory-app/         # Flask CRUD API -> movies_db
└── Vagrantfile
```

## Environment variables

All credentials and connection details live in `.env` (committed on purpose for
this exercise). No service hard-codes credentials. Required variables:

| Variable | Purpose |
|----------|---------|
| `INVENTORY_DB_HOST/PORT/NAME/USER/PASSWORD` | Postgres connection for `movies_db` |
| `BILLING_DB_HOST/PORT/NAME/USER/PASSWORD` | Postgres connection for `billing_db` |
| `RABBITMQ_HOST/PORT/USER/PASSWORD/QUEUE` | RabbitMQ broker + `billing_queue` |
| `INVENTORY_API_HOST/PORT` | Where the Inventory API binds/listens (`8080`) |
| `GATEWAY_HOST/PORT` | Where the API Gateway binds/listens (`9000`) |

> **Cross-VM note:** the shared `.env` uses `localhost` for local development.
> The Vagrant setup scripts override the relevant values per VM before starting
> each app (e.g. the gateway is pointed at `192.168.56.11` for Inventory and
> `192.168.56.12` for RabbitMQ). See `scripts/setup_*.sh`.

## Setup & run locally (pre-VM)

Each app uses its own virtual environment. From the repo root:

```bash
# 0. Prerequisites: PostgreSQL and RabbitMQ running locally, then create the
#    databases and users from .env (see scripts/*.sql for the schemas).

# 1. Inventory API (listens on :8080)
cd srcs/inventory-app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py

# 2. Billing API (RabbitMQ consumer, no HTTP)
cd srcs/billing-app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py

# 3. API Gateway (listens on :9000)
cd srcs/api-gateway-app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python server.py
```

Quick smoke test after all three are up:

```bash
curl -X POST http://localhost:9000/api/movies \
     -H "Content-Type: application/json" \
     -d '{"title": "Dune", "description": "Sci-fi epic"}'

curl -X POST http://localhost:9000/api/billing \
     -H "Content-Type: application/json" \
     -d '{"user_id": "3", "number_of_items": "5", "total_amount": "180"}'
```

## Setup & run with Vagrant

```bash
vagrant up        # creates & provisions all three VMs
vagrant status    # show VM states
vagrant ssh gateway-vm    # access a specific VM (also: inventory-vm, billing-vm)
```

Each setup script installs Python, PostgreSQL and/or RabbitMQ as needed,
creates the databases and tables, sets up the Python venv, installs
dependencies and registers the app with PM2 (with auto-resurrect on reboot).

End-to-end checks from `gateway-vm` (the gateway reaches Inventory over
`192.168.56.11:8080` and RabbitMQ over `192.168.56.12:5672`):

```bash
vagrant ssh gateway-vm -- curl -s http://localhost:9000/health
vagrant ssh gateway-vm -- curl -s http://localhost:9000/api/movies
vagrant ssh gateway-vm -- curl -s -X POST http://localhost:9000/api/billing \
    -H "Content-Type: application/json" \
    -d '{"user_id": "3", "number_of_items": "5", "total_amount": "180"}'
```

## Testing

- **Postman** — import `docs/postman_collection.json` (requests target the
  gateway at `http://192.168.56.10:9000`, the gateway-vm private IP; the
  `baseUrl` collection variable can be overridden). Contains tests for every
  Inventory
  endpoint (list, search, create, get-by-id, update, delete-by-id, delete-all)
  and `POST /api/billing`.
- **OpenAPI** — `docs/openapi.yaml` documents the API Gateway endpoints.
- **Billing resilience** — `docs/billing-test-steps.md` walks through the
  publish / stop / restart scenarios (with PM2).
- **Local integration smoke test** — with all three services running locally,
  run:

  ```bash
  ./scripts/test_local.sh
  ```

## Managing apps with PM2 (in a VM)

```bash
sudo pm2 list            # list managed apps
sudo pm2 stop billing-app
sudo pm2 start billing-app
sudo pm2 restart billing-app
sudo pm2 logs billing-app
```

PM2 keeps the apps alive across crashes; `sudo pm2 save` + `pm2 startup`
ensure they come back after a VM reboot. This is the tool used to prove the
Billing API's queue-based resilience (see `docs/billing-test-steps.md`).

## Design choices

- **Flask + SQLAlchemy** — lightweight, standard Python stack for simple
  RESTful services; SQLAlchemy maps `Movie`/`Order` models to the `movies` and
  `orders` tables.
- **pika (`BlockingConnection`)** — simple synchronous RabbitMQ client. The
  queue is declared **durable** and messages are published **persistent**
  (`delivery_mode=2`), so no messages are lost when the Billing API or the
  broker is down.
- **Billing API has no HTTP surface** — it is a pure worker: connect to RabbitMQ
  (with retries at startup), drain pending messages, ack only after a
  successful DB insert. Malformed messages are acked and discarded; transient
  failures are requeued.
- **API Gateway as a transparent proxy** for `/api/movies` — it forwards the
  HTTP method, query params, and JSON body to the Inventory API and returns the
  response verbatim, so the Inventory API stays the single source of truth.
- **One VM per service** — clear separation of concerns and isolated failures,
  matching the exercise's VM layout (`gateway` / `inventory` / `billing`).
- **`.env` as the single config source** — committed as required by the
  exercise; Vagrant loads it via `vagrant-dotenv` and the per-VM scripts
  override host-specific values (see above).
- **PM2 for resilience** — not just a process manager but the test harness for
  the "stop the consumer, keep publishing, restart, watch it drain" scenario.

## Useful references

- Exercise spec: `crud-master.md` (project root)
- Task board: `docs/scrum-task-board.md`
- OpenAPI: `docs/openapi.yaml`
- Postman: `docs/postman_collection.json`
- Billing test steps: `docs/billing-test-steps.md`
