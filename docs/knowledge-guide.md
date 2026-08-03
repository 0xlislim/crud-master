# CRUD Master — Knowledge Guide

Everything you need to understand, explain, and defend this project. Read this
top-to-bottom before the audit. It covers the architecture, each service, the
important concepts, and the exact problems solved along the way.

---

## 1. What the project is

A **movie streaming platform** built to learn **microservices**. Instead of one
big application, the work is split into three small Python services plus an API
Gateway that is the single entry point for clients.

The three pieces:

| Service | Job | Talks to | Port |
|---------|-----|----------|------|
| **API Gateway** | Single entry point; routes requests to the right service | Inventory (HTTP), Billing (RabbitMQ) | 9000 |
| **Inventory API** | CRUD for movies | PostgreSQL `movies_db` | 8080 |
| **Billing API** | Async order processor | RabbitMQ (in) → PostgreSQL `billing_db` (out) | none (no HTTP) |

Key idea: the Gateway uses **two different protocols** depending on the backend:
- **HTTP** to talk to the Inventory API.
- **RabbitMQ (a message queue)** to hand work to the Billing API.

Why? Billing can be slow and must survive outages; a message queue lets the
client "fire and forget" and lets the Billing API process work asynchronously
later.

---

## 2. Architecture & data flow

```
                    ┌──────────────────────────────┐
                    │        API Gateway (9000)     │
                    └──────┬───────────────┬───────┘
                           │ HTTP          │ RabbitMQ
                           │               ▼
                ┌──────────▼────────┐   ┌──────────────────────┐
                │  Inventory API    │   │      Billing API      │
                │      (8080)       │   │  (RabbitMQ consumer)  │
                └──────────┬────────┘   └──────────┬───────────┘
                           │ SQLAlchemy            │ SQLAlchemy
                    ┌──────▼────────┐       ┌──────▼─────────────┐
                    │   movies_db   │       │      billing_db     │
                    └───────────────┘       └────────────────────┘
```

**Forward (Inventory)** flow:
1. Client → `POST/GET/... http://gateway:9000/api/movies`
2. Gateway proxies the request **exactly as-is** (method, query, body) to
   `inventory:8080/api/movies`.
3. Inventory reads/writes `movies_db`, returns a JSON response.
4. Gateway copies that response back **verbatim** (same status + body).

**Reverse/queue (Billing)** flow:
1. Client → `POST /api/billing` with a JSON order body.
2. Gateway **publishes** that body to a RabbitMQ queue (`billing_queue`); the
   client immediately gets `{"message": "Message posted"}`.
3. RabbitMQ stores the message (persistent).
4. Billing API **consumes** it, inserts a row into `billing_db.orders`, then
   **acknowledges** the message.
5. If the Billing API is down, messages wait in the queue and get processed
   when it comes back. The Gateway never blocks on Billing being online.

---

## 3. The stack & tools (and why)

- **Python 3 + Flask** — tiny, standard web framework for the two HTTP-facing apps.
- **Flask-SQLAlchemy** — ORM: maps Python classes to DB tables (used by Inventory).
- **SQLAlchemy Core** — used directly by Billing (no Flask).
- **psycopg2** — the actual Postgres driver SQLAlchemy uses under the hood.
- **pika** — Python client for RabbitMQ (both publisher and consumer).
- **PostgreSQL** — relational DB, one database per service.
- **RabbitMQ** — message broker; the queue between Gateway and Billing.
- **Vagrant + VirtualBox** — one VM per service (real separation).
- **PM2** — process manager that keeps the Python apps running and lets us
  test resilience (stop/start on purpose).
- **Postman** — API testing (tests are exported in `docs/postman_collection.json`).

---

## 3.5 Project structure

```console
.
├── README.md               # how to run/test — read this first
├── Vagrantfile             # defines the 3 VMs + reads .env
├── .env                    # all credentials/URLs (committed — required by the exercise)
├── config.yaml             # optional high-level config (not critical)
├── scripts/
│   ├── setup_gateway.sh    # provisions gateway-vm
│   ├── setup_inventory.sh  # provisions inventory-vm
│   ├── setup_billing.sh    # provisions billing-vm
│   ├── init_movies_db.sql  # movies table + (grants in setup script)
│   ├── init_billing_db.sql # orders table
│   └── test_local.sh       # local integration smoke test
├── docs/
│   ├── openapi.yaml            # API Gateway OpenAPI doc (audit item)
│   ├── postman_collection.json # exported Postman tests (audit item)
│   ├── billing-test-steps.md   # resilience scenarios
│   └── manual-test-commands.md # the copy-paste test walkthrough
└── srcs/
    ├── api-gateway-app/     # Gateway: Flask proxy + RabbitMQ publisher
    │   ├── server.py        # entrypoint
    │   └── app/{__init__, routes, publisher}.py
    ├── inventory-app/       # Flask CRUD API
    │   ├── server.py
    │   └── app/{__init__, routes, models}.py
    └── billing-app/        # RabbitMQ consumer → DB
        ├── server.py
        └── app/{consumer, models}.py
```

Each service has its own venv and its own `requirements.txt`. Every app runs
`python server.py`.

---

## 4. Inventory API (detailed)

**Database:** `movies_db`, table `movies`.

```
movies
  id          SERIAL PRIMARY KEY  (auto-generated)
  title       VARCHAR(255) NOT NULL
  description TEXT
```

**Model** (`app/models.py`):

```python
class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
```

**Routes** (`app/routes.py`) — all under `/api/movies`:

| Method & path | Behavior | Success |
|---------------|----------|---------|
| `GET /api/movies` | list all | 200 |
| `GET /api/movies?title=X` | filter where title contains X (case-insensitive, `LIKE %X%`) | 200 |
| `POST /api/movies` | create (needs `title`) | 201 |
| `PUT /api/movies/<id>` | update by id | 200 |
| `DELETE /api/movies/<id>` | delete one | 200 |
| `DELETE /api/movies` | delete all | 200 |
| `GET /api/movies/<id>` | get one | 200 (404 if missing) |

**Application factory** (`app/__init__.py`):
- `load_dotenv()` reads the `.env`.
- Builds the DB URI and registers the SQLAlchemy `db`.
- Registers the blueprint routes.
- Calls `db.create_all()` (creates tables if the DB is reachable).

**Important detail — the URI** `postgresql://user:pass@host:port/db`. The
password is URL-encoded with `quote_plus()` because the real password contains
an `@` which would otherwise be parsed as the host separator:

```python
from urllib.parse import quote_plus
db_uri = f"postgresql://{quote_plus(db_user)}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"
```

---

## 5. Billing API deep-dive

The Billing API has **no HTTP endpoint**. It is a **worker process**:

```
(body JSON) --publish--> billing_queue --> consume --> parse --> INSERT into billing_db.orders --> ACK
```

**Server loop** (`app/consumer.py`) — `start_consumer()`:
1. Loads `.env`.
2. Connects to PostgreSQL (retries ~10×, 3s apart) and creates
   `sessionmaker` + the `orders` table.
3. Connects to RabbitMQ (retries ~15×, 3s apart).
4. Declares `billing_queue` **durable** (survives broker restarts).
5. Sets `basic_qos(prefetch_count=1)` (fair dispatch).
6. Registers a `callback` that runs per message:
   - decode JSON, cast `user_id`, `number_of_items`, `total_amount` to int/float
   - insert an `Order`
   - `session.commit()`
   - `ch.basic_ack()` — acknowledge only after successful insert
   - on malformed JSON → ack (and discard) to avoid infinite re-delivery
   - on any other error → `basic_nack(requeue=True)` and retry
7. Listens for SIGTERM to shut down cleanly.

**Why it drains the queue on startup:** because it just connects and starts
consuming, any messages that piled up while it was stopped are processed
automatically.

**Model** (`app/models.py`): `orders` table:
```
id, user_id INTEGER, number_of_items INTEGER, total_amount FLOAT/NUMERIC
```

**Same `quote_plus` DB URI trick** as Inventory.

---

## 6. API Gateway deep-dive

**Server** (`server.py`): creates the app factory, runs on `GATEWAY_HOST:9000`.

**Routes** (`app/routes.py`):

- `GET /health` → `{"status":"ok", ...}` (liveness check).

- `GET/POST/DELETE /api/movies` and `/api/movies/<id>` → **proxy** to
  Inventory. It forwards method, query params, and JSON body, and returns the
  Inventory response **verbatim** (same status, headers, body). If Inventory
  is unreachable it returns `502`.

- `POST /api/billing` → reads the JSON body and publishes it to RabbitMQ
  `billing_queue`. Returns `{"message": "Message posted"}`. It only needs the
  **broker**, not the Billing API.

Python **publisher** (`app/publisher.py`):
- Opens a `pika.BlockingConnection`
- `queue_declare(durable=True)`
- `basic_publish(..., body=json.dumps(msg), properties=BasicProperties(delivery_mode=2))`
  - `delivery_mode=2` = **persistent** message (survives broker restarts).

---

## 7. The `.env` and environment variables

One `.env` file at repo root is the **single source of config**. Vagrant loads
it, and every app reads the variables via `load_dotenv()`. Nothing is
hard-coded (we even removed the DB password defaults from source).

| Group | Variables |
|-------|-----------|
| Inventory DB | `INVENTORY_DB_HOST/PORT/NAME/USER/PASSWORD` (`movies_db`) |
| Billing DB | `BILLING_DB_HOST/PORT/NAME/USER/PASSWORD` (`billing_db`) |
| RabbitMQ | `RABBITMQ_HOST/PORT/USER/PASSWORD/QUEUE` (`billing_queue`) |
| Inventory app | `INVENTORY_API_HOST/PORT` (8080) |
| Gateway app | `GATEWAY_HOST/PORT` (9000) |

**Committed on purpose**: the exercise *requires* committing `.env` even though
in the real world you would commit only a `.env.example`. No secrets should be
hard-coded in source.

---

## 7. Vagrant & the VMs

`Vagrantfile` defines exactly 3 VMs (`ubuntu/jammy64`), each with its own
function:

```
gateway-vm   192.168.56.10   runs api-gateway-app only
inventory-vm 192.168.56.11   runs inventory-app + movies_db
billing-vm   192.168.56.12   runs billing-app + billing_db + RabbitMQ
```

- The `setup_*.sh` scripts provision each VM: install Python/Postgres/RabbitMQ/
  Node+PM2, create users & databases, apply `init_*.sql`, create the venv,
  install `requirements.txt`, and register the app in PM2.
- The `.env` is loaded in the Vagrantfile and passed to the provision scripts
  through `env: ENV.to_h`.
- `vagrant ssh <vm>` shells in, so testing a service is just a curl inside that
  VM.

**Cross-VM catch:** the shared `.env` uses `localhost`, but the Gateway must
reach Inventory (on 192.168.56.11) and RabbitMQ (on 192.168.56.12) across the
network. The per-VM addresses are set in PM2 **ecosystem.config.js** files
(Gateway: `INVENTORY_API_HOST=192.168.56.11`, `RABBITMQ_HOST=192.168.56.12`);
Inventory binds `0.0.0.0` so other VMs can reach it.

Why not plain exports in the shell? Because `sudo` (used by `pm2 start`) resets
the environment; PM2 `env` values are applied by PM2 itself to the child
process, so they survive sudo.

---

## 9. PM2 — process management & resilience

PM2 keeps the Python processes alive and lets you test resilience:

```bash
sudo pm2 list                 # see the managed apps
sudo pm2 stop billing-app     # stop the Billing consumer on purpose
sudo pm2 start billing-app    # start it again
sudo pm2 restart inventory-app# restart to pick up code changes
sudo pm2 logs billing-app     # tail live logs
sudo pm2 save                 # snapshot the process list
sudo pm2 startup systemd      # enable auto-restart on boot
```

Because of `pm2 save` + `pm2 startup`, even a VM reboot brings the apps back.
This is what the resilience test relies on: **stop the Billing app, keep
publishing, restart, watch the queue drain.**

---

## 10. The problems we hit and fixed (great audit talking points)

1. **Cross-VM DNS**: shared `.env` said `localhost` → gateway couldn't find
   Inventory/RabbitMQ. Solved with PM2 `ecosystem.config.js` `env` vars.
2. **Inventory listened on loopback only** → gateway couldn't reach it. Set
   `INVENTORY_API_HOST=0.0.0.0`.
3. **RabbitMQ `guest` is loopback-only** → a non-loopback connection from the
   gateway was refused. We created a dedicated RabbitMQ `crud_billing` user in
   `.env` and provisioned it in `setup_billing.sh` (also enabled the management
   UI on port 15672).
4. **Password with `@` breaks the URI** → `12qw!@QW` parsed as host `QW@localhost`.
   Fixed with `urllib.parse.quote_plus()`.
5. **Tables owned by postgres superuser** → app users had no privileges.
   Added `GRANT ALL PRIVILEGES ON ALL TABLES/SEQUENCES IN SCHEMA public`.
6. **Host-created `venv` had dangling Python symlinks inside the VM** (the
   path pointed at the host, not the VM). Fixed by recreating the venv in the
   VM.
7. **`vagrant-dotenv` plugin incompatible** with Vagrant's Ruby 3.2
   (`File.exists?` was removed). Replaced with a small manual parse of `.env`
   in the Vagrantfile.
8. **Hard-coded DB password defaults in source** → removed so credentials live
   only in `.env`.

---

## 11. How to test everything (short version; full = `docs/manual-test-commands.md`)

```bash
vagrant up && vagrant status     # start + check the 3 VMs

# --- Inventory through the gateway ---
vagrant ssh gateway-vm -- 'curl -s -X POST http://localhost:9000/api/movies \\
     -H "Content-Type: application/json" -d "{\"title\":\"Dune\",\"description\":\"Sci-fi\"}"; echo'
vagrant ssh gateway-vm -- 'curl -s http://localhost:9000/api/movies; echo'
vagrant ssh gateway-vm -- 'curl -s "http://localhost:9000/api/movies?title=Dune"; echo'

# --- Billing (publish → queue → consumer → DB) ---
vagrant ssh gateway-vm -- 'curl -s -X POST http://localhost:9000/api/billing \\
     -H "Content-Type: application/json" -d "{\"user_id\":\"3\",\"number_of_items\":\"5\",\"total_amount\":\"180\"}"; echo'
vagrant ssh billing-vm -- 'sudo -u postgres psql -d billing_db -c "SELECT * FROM orders;"'

# --- Resilience ---
vagrant ssh billing-vm -- 'sudo pm2 stop billing-app'
vagrant ssh gateway-vm -- 'for i in 1 2 3; do curl -s -X POST http://localhost:9000/api/billing \\
     -H "Content-Type: application/json" -d "{\"user_id\":\"$i\",\"number_of_items\":\"2\",\"total_amount\":\"99\"}"; echo; done'
vagrant ssh billing-vm -- 'sudo rabbitmqctl list_queues name messages'  # shows backlog
vagrant ssh billing-vm -- 'sudo pm2 start billing-app; sleep 5'
vagrant ssh billing-vm -- 'sudo -u postgres psql -d billing_db -c "SELECT * FROM orders;"' # drained
```

---

## 12. Audit Q&A cheat-sheet

**Q: Why HTTP for Inventory but RabbitMQ for Billing?**
Inventory is synchronous CRUD — clients need the answer now, HTTP is natural.
Billing is asynchronous, tolerant to downtime; a queue decouples the client and
Billing and won't lose work if the Billing app is down.

**Q: Why does the queue survive the Billing app crashing?**
The queue is `durable` and messages are sent `delivery_mode=2` (persistent).
RabbitMQ keeps them on disk until a consumer acknowledges them. When Billing
returns, it connects and starts consuming whatever is pending.

**Q: Why ack only after the DB insert?**
If we acked before the insert and the insert fail, the message would be lost.
Ack-after-success is "at-least-once" delivery. On DB error we `nack(requeue)`
to retry; on malformed JSON we ack/drop (can never be processed).

**Q: How does the database get its tables?**
The `init_*.sql` scripts create them; the apps also `create_all()` at startup.

**Q: Where do credentials live?**
Only in `.env` (committed for the exercise). Source code reads them with
`os.getenv()` and contains no hard-coded secrets.

**Q: Explain the two databases.**
`movies_db.movies` (id, title, description) and `billing_db.orders`
(id, user_id, number_of_items, total_amount).

> Note for the auditor: the exercise subject says the billing database is
> `billing_db` (table `orders`). Some checklist text loosely calls it
> `orders_db`—but `billing_db` is the spec and what we implemented.

---

## 13. Vocabulary

- **Microservices**: splitting one app into small independent services.
- **API Gateway**: a facade that routes client requests to the right backend.
- **Message queue / broker**: a buffer between services (RabbitMQ here).
- **Publish**: send a message into a queue.
- **Consume**: pull a message out of a queue.
- **ACK**: acknowledge; tells the broker the message was successfully processed.
- **Durable/persistent**: stored on disk, survives restarts.
- **ORM**: object-relational mapper (SQLAlchemy maps classes ↔ tables).
- **Vagrant**: tool to define/start VMs in code.
- **PM2**: process manager that keeps apps running + enables resilience tests.