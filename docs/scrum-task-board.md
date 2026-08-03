# CRUD Master — Scrum Task Board

**Team:** 2 members (A, B)

## Task Backlog

| # | Task | Owner | Priority | Est. | Status |
|---|------|-------|----------|------|--------|
| 1 | Set up repo structure, `.gitignore`, `.env` skeleton | Both | High | 1h | Done |
| 2 | Inventory API: Flask + SQLAlchemy skeleton, connect to `movies_db` | A | High | 2h | Done |
| 3 | Inventory API: `GET/POST/DELETE /api/movies` | A | High | 3h | Done |
| 4 | Inventory API: `GET/PUT/DELETE /api/movies/<id>` | A | High | 2h | Done |
| 5 | Inventory API: Postman tests + export collection | A | Med | 1.5h | Done — `docs/postman_collection.json` |
| 6 | Billing API: RabbitMQ consumer (`pika`) skeleton on `billing_queue` | A | High | 2h | Done |
| 7 | Billing API: parse message → insert into `billing_db.orders` → ack | A | High | 2h | Done |
| 8 | Billing API: process pending messages on startup (resilience test) | A | High | 1.5h | Done |
| 9 | Billing API: test steps doc (publish/stop/restart scenarios) | A | Med | 1h | Done — `docs/billing-test-steps.md` |
| 10 | API Gateway: skeleton Flask app | B | High | 1h | Done |
| 11 | API Gateway: proxy `/api/movies` → Inventory API (HTTP) | B | High | 2h | Done |
| 12 | API Gateway: `POST /api/billing` → publish to `billing_queue` | B | High | 2h | Done |
| 13 | API Gateway: OpenAPI/SwaggerHub documentation | B | Med | 2h | Done — `docs/openapi.yaml` |
| 14 | `Vagrantfile`: define 3 VMs (gateway/inventory/billing) | B | High | 2h | Done |
| 15 | `scripts/`: install Python, Postgres, RabbitMQ, PM2 per VM | B | High | 3h | Done |
| 16 | `scripts/`: DB init (create `movies_db`, `billing_db`, tables) | B | High | 1.5h | Done |
| 17 | Wire `.env` vars through Vagrant into services | B | High | 1.5h | Done |
| 18 | PM2 config for each app (start/stop/list/restart) | B | Med | 1h | Done — `ecosystem.config.js` + resurrect |
| 19 | README.md: architecture, stack, setup/run/test, env vars | B | High | 2h | Done |
| 20 | Integration test: Gateway ↔ Inventory (local, pre-VM) | Both | High | 1h | Done — `scripts/test_local.sh` |
| 21 | Integration test: Gateway ↔ RabbitMQ ↔ Billing (local, pre-VM) | Both | High | 1h | Done — `scripts/test_local.sh` |
| 22 | Full VM test: `vagrant up/status/ssh`, PM2 resilience test on billing-app | Both | High | 2h | Done — verified cross-VM + resilience |
| 23 | Final review: README, Postman collection, OpenAPI doc | Both | Med | 1h | To Do |

## Sprint Plan

### Sprint 1 (Days 1–2)
- Member A: Tasks 1–9
- Member B: Tasks 10–17
- Build core services and infra independently, in parallel.

### Sprint 2 (Days 3–4)
- Both: Tasks 18–21
- Wire everything together and test locally.

### Sprint 3 (Day 5)
- Both: Tasks 22–23
- Full VM validation and audit prep.

## Ownership Legend
- **A** — Inventory & Billing APIs (services side)
- **B** — API Gateway, Infrastructure & Documentation
- **Both** — Shared/integration tasks
