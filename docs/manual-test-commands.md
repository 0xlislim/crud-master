# Manual Test — Command Walkthrough

A copy-paste guide of the exact commands used to validate the CRUD Master
infrastructure on the 3 VMs, with what each does and what to expect. Work
through the sections in order.

Two ways to run commands in a VM:

```bash
# Option A (from host): run one command inside a VM
vagrant ssh gateway-vm -- 'sudo pm2 list'

# Option B (from host): open an interactive shell in the VM
vagrant ssh gateway-vm
# then type commands normally (no quotes)
```

---

## 0. Start the environment

```bash
# from the project root (/home/aesslima/crud-master)
vagrant up            # create + provision all 3 VMs (first run downloads the box)
vagrant status        # show state of inventory-vm, billing-vm, gateway-vm
```

Expected `vagrant status`:

```
inventory-vm              running (virtualbox)
billing-vm                running (virtualbox)
gateway-vm                running (virtualbox)
```

> Tear everything down afterwards with `vagrant destroy -f` (recreate with
> `vagrant up`).

---

## 1. Look at the process manager (PM2) on each VM

The three apps are registered with PM2 and auto-start on boot.

```bash
vagrant ssh inventory-vm -- 'sudo pm2 list'
vagrant ssh billing-vm   -- 'sudo pm2 list'
vagrant ssh gateway-vm   -- 'sudo pm2 list'
```

Expected: one app per VM, `status online`:

| VM          | app name          |
|-------------|-------------------|
| inventory-vm| inventory-app     |
| billing-vm  | billing-app       |
| gateway-vm  | api-gateway-app   |

**What's going on:** PM2 is the process manager. It keeps each Python service
running, restarts it on crash, and (with `pm2 save` + `pm2 startup`) resurrects
it after a VM reboot. This is the tool the exercise uses for the resilience test.

---

## 2. Watch the services' logs

```bash
# Inventory API (Flask, shows the debug server startup)
vagrant ssh inventory-vm -- 'sudo pm2 logs inventory-app --lines 15 --nostream'

# Billing API (RabbitMQ consumer; shows DB + broker connection)
vagrant ssh billing-vm -- 'sudo pm2 logs billing-app --lines 15 --nostream'

# API Gateway (Flask)
vagrant ssh gateway-vm -- 'sudo pm2 logs api-gateway-app --lines 15 --nostream'
```

Expected (billing-vm) — the important lines:

```
Starting Billing API (RabbitMQ Consumer)...
Initializing Database Connection...
Successfully connected to the database!
Connecting to RabbitMQ...
Successfully connected to RabbitMQ!
Waiting for messages in 'billing_queue'... Press CTRL+C to exit.
```

**What's going on:** the Billing API has no HTTP endpoint. It is a pure worker:
it connects to PostgreSQL and RabbitMQ, then blocks waiting for queue messages.

---

## 3. Inventory API, direct on its VM (no gateway)

Inventory is exposed on port 8080. Test it straight from inventory-vm:

```bash
vagrant ssh inventory-vm -- 'curl -s http://localhost:8080/api/movies; echo'
vagrant ssh inventory-vm -- 'curl -s -X POST http://localhost:8080/api/movies -H "Content-Type: application/json" -d "{\"title\":\"Dune\",\"description\":\"Sci-fi epic\"}"; echo'
```

Expected: `[]` first, then a JSON movie object with an auto-generated `id`.

**What's going on:** you're hitting the Flask CRUD API directly, which reads
from / writes to the `movies` table in PostgreSQL (`movies_db`).

---

## 4. Same requests through the API Gateway (the single entry point)

Everything a client does goes through the gateway on port 9000. The gateway
forwards `/api/movies*` to the Inventory API over **HTTP** on `192.168.56.11`.

```bash
# health check
vagrant ssh gateway-vm -- 'curl -s http://localhost:9000/health; echo'

# list movies (should include the one you just created)
vagrant ssh gateway-vm -- 'curl -s http://localhost:9000/api/movies; echo'

# create one through the gateway
vagrant ssh gateway-vm -- 'curl -s -X POST http://localhost:9000/api/movies -H "Content-Type: application/json" -d "{\"title\":\"Blade Runner\",\"description\":\"Neo-noir\"}"; echo'

# read a single movie by id (use the id from the create response)
vagrant ssh gateway-vm -- 'curl -s http://localhost:9000/api/movies/1; echo'

# update by id
vagrant ssh gateway-vm -- 'curl -s -X PUT http://localhost:9000/api/movies/1 -H "Content-Type: application/json" -d "{\"title\":\"Dune (2021)\"}"; echo'

# search by title (the ?title= filter)
vagrant ssh gateway-vm -- 'curl -s "http://localhost:9000/api/movies?title=Dune"; echo'

# delete one
vagrant ssh gateway-vm -- 'curl -s -X DELETE http://localhost:9000/api/movies/1; echo'

# delete ALL movies
vagrant ssh gateway-vm -- 'curl -s -X DELETE http://localhost:9000/api/movies; echo'
```

**What's going on:** the gateway is a transparent proxy. It forwards the method,
query string and body to the Inventory API and returns the response **verbatim**
(status code + body). Compare section 3 vs 4 — same data, now routed through the
gateway from a different VM.

---

## 5. Billing: HTTP publish -> RabbitMQ -> consumer -> PostgreSQL

`POST /api/billing` does **not** insert anything into a database. The gateway
publishes the JSON body to RabbitMQ's `billing_queue`. The Billing API consumer
on billing-vm picks it up, inserts a row into `orders` (billing_db) and
acknowledges the message.

```bash
# 1) publish an order via the gateway
vagrant ssh gateway-vm -- 'curl -s -X POST http://localhost:9000/api/billing -H "Content-Type: application/json" -d "{\"user_id\":\"3\",\"number_of_items\":\"5\",\"total_amount\":\"180\"}"; echo'
#   -> {"message": "Message posted"}

# 2) check the orders table on billing-vm (should now contain 1 row)
vagrant ssh billing-vm -- 'sudo -u postgres psql -d billing_db -c "SELECT * FROM orders ORDER BY id;"'

# 3) check the queue is drained (consumer acknowledged the message)
vagrant ssh billing-vm -- 'sudo rabbitmqctl list_queues name messages'
#   -> billing_queue	0
```

**What's going on:** three moving parts. (1) gateway → RabbitMQ (publish only,
needs only the broker); (2) RabbitMQ → Billing API (the consumer); (3) Billing
API → PostgreSQL (the insert). The message format: `user_id`, `number_of_items`,
`total_amount`, all sent as strings and parsed by the consumer.

---

## 6. Resilience test: stop the consumer, keep publishing, restart

This is the scenario the exercise (and PM2) is really about. If the Billing API
is down, orders must **still be accepted** at the gateway and stored in the
queue; they must be processed only once the consumer is back.

### 6a. Stop the Billing API consumer

```bash
vagrant ssh billing-vm -- 'sudo pm2 stop billing-app'
vagrant ssh billing-vm -- 'sudo pm2 list'     # status: stopped
```

### 6b. Publish 3 orders while it is down

```bash
vagrant ssh gateway-vm -- 'for i in 1 2 3; do curl -s -X POST http://localhost:9000/api/billing -H "Content-Type: application/json" -d "{\"user_id\":\"$i\",\"number_of_items\":\"2\",\"total_amount\":\"99\"}"; echo; done'
#   -> {"message": "Message posted"}  x3   (still succeeds!)
```

### 6c. Verify: orders NOT updated, but 3 messages queued

```bash
vagrant ssh billing-vm -- 'sudo -u postgres psql -d billing_db -tAc "SELECT count(*) FROM orders;"'
#   -> 1   (unchanged: the pending orders were NOT inserted)

vagrant ssh billing-vm -- 'sudo rabbitmqctl list_queues name messages messages_unacknowledged'
#   -> billing_queue	3	0   (3 ready messages, 0 in-flight)
```

### 6d. Restart the consumer and watch it drain

```bash
vagrant ssh billing-vm -- 'sudo pm2 start billing-app'
sleep 5
vagrant ssh billing-vm -- 'sudo -u postgres psql -d billing_db -c "SELECT * FROM orders ORDER BY id;"'
#   -> 4 rows now (1 old + the 3 new ones)
vagrant ssh billing-vm -- 'sudo rabbitmqctl list_queues name messages'
#   -> billing_queue	0   (all 3 acknowledged and processed)
```

**What's going on:** because the queue is **durable** and messages are published
**persistent**, RabbitMQ holds them while no consumer is connected. On startup
the Billing API connects, finds the pending messages and processes them —
"process pending messages on startup" from the spec.

---

## 7. Check PM2 auto-resurrect is configured

```bash
vagrant ssh billing-vm -- 'systemctl is-enabled pm2-root'
#   -> enabled
```

**What's going on:** `pm2 save` snapshots the process list to
`/root/.pm2/dump.pm2` and `pm2 startup systemd` creates a systemd unit. After a
VM reboot (`vagrant reload billing-vm`) the apps start again automatically.

---

## 8. Useful admin / debugging commands

```bash
# Verify the shared folder is mounted in the VM (apps live here)
vagrant ssh gateway-vm -- 'ls /vagrant/srcs'

# Check the DB user has privileges on the movies table
vagrant ssh inventory-vm -- 'sudo -u postgres psql -d movies_db -c "\dp movies"'

# Confirm the gateway env points at the other VMs
vagrant ssh gateway-vm -- 'sudo pm2 env 0 | grep -E "INVENTORY_API_HOST|RABBITMQ_HOST"'
#   -> INVENTORY_API_HOST: 192.168.56.11
#   -> RABBITMQ_HOST: 192.168.56.12

# Restart an app after editing code (code is shared via /vagrant)
vagrant ssh inventory-vm -- 'sudo pm2 restart inventory-app'

# Follow live logs
vagrant ssh billing-vm -- 'sudo pm2 logs billing-app'

# Reload / reboot a VM to prove resurrect works
vagrant reload billing-vm
vagrant ssh billing-vm -- 'sudo pm2 list'
```

---

## Quick reference: what talks to what

```
client
  │
  ▼
gateway-vm  :9000        ─── HTTP ───▶ inventory-vm :8080  ──▶ movies_db (PostgreSQL)
  │
  └── RabbitMQ(billing-vm :5672) billing_queue ──▶ billing-app (consumer) ──▶ billing_db.orders
```

- Inventory: DB `movies_db`, table `movies` (`id`, `title`, `description`).
- Billing: DB `billing_db`, table `orders` (`id`, `user_id`, `number_of_items`,
  `total_amount`).
- All credentials/URLs come from `.env` (committed), not hard-coded in the apps.
