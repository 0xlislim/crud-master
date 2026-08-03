# CRUD Master — Implementation Plan

Status assessment vs. the Scrum task board (`docs/scrum-task-board.md`) and the
assignment spec (`crud-master.md`).

## Already implemented & committed (board statuses are stale)

- **Tasks 1–4** — Repo structure, `.gitignore`, `.env`, Inventory API CRUD + title filter on `movies_db`
- **Tasks 6–8** — Billing API pika consumer, parse → insert → ack, startup pending-message processing
- **Tasks 10–13** — API Gateway skeleton, `/api/movies` HTTP proxy, `/api/billing` RabbitMQ publisher, OpenAPI doc (`docs/openapi.yaml`)
- **Tasks 14–17** — `Vagrantfile` (3 VMs), `scripts/` (install + DB init), `.env` wired through Vagrant
- **Task 18** — PM2 start + resurrect in each setup script

## Missing / incomplete

- **Task 5** — no Postman collection (required at audit)
- **Task 9** — no billing test-steps doc (publish/stop/restart scenarios)
- **Task 19** — README is a skeleton (placeholders, dead `resources/crud-master-diagram.png` ref)
- **Tasks 20–21** — no local integration test artifacts
- **Task 22** — VM test not run/verified

## Critical bug to fix first

The shared `.env` uses `localhost` for `INVENTORY_API_HOST` and `RABBITMQ_HOST`,
and Vagrant passes `ENV.to_h` verbatim to every VM. On `gateway-vm`, `localhost`
points at nothing:

- Gateway can't reach the Inventory API on `inventory-vm`
- Gateway can't reach RabbitMQ on `billing-vm`
- Inventory app binds to `localhost` only, so gateway-vm can't reach it at all

Fix via per-VM env overrides in the setup scripts (python-dotenv `load_dotenv()`
is `override=False`, so exported vars win over the shared `.env`).

## Phases

### Phase 1 — Fix cross-VM connectivity
- `scripts/setup_gateway.sh`: export `INVENTORY_API_HOST=192.168.56.11`, `RABBITMQ_HOST=192.168.56.12` before `pm2 start`
- `scripts/setup_inventory.sh`: export `INVENTORY_API_HOST=0.0.0.0` before `pm2 start`

### Phase 2 — Missing audit deliverables
- `docs/postman_collection.json` — Postman v2.1 export, one test per endpoint
- `docs/billing-test-steps.md` — resilience scenarios (publish / stop / restart)
- Finish `README.md` — architecture, env-var table, design choices, local + VM run/test steps

### Phase 3 — Local integration tests
- `scripts/test_local.sh` — curl checks for Gateway↔Inventory and Gateway↔RabbitMQ↔Billing (+ resilience scenario)

### Phase 4 — Full VM validation (Task 22)
- `vagrant up`, `vagrant status`, `vagrant ssh` sanity on all 3 VMs
- End-to-end via gateway-vm → inventory-vm (HTTP) and → billing-vm (RabbitMQ)
- PM2 resilience test: stop billing-app → POST `/api/billing` → verify orders unchanged → start billing-app → verify pending processed

### Phase 5 — Review + board update
- Update `docs/scrum-task-board.md` statuses to reflect reality
- Verify doc references resolve; `py_compile` edited Python files
- All changes left uncommitted for review
