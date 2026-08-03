#!/usr/bin/env bash
# Local integration smoke test (pre-VM).
#
# Requires all three services running locally:
#   Inventory API (:8080), Billing API (RabbitMQ consumer), API Gateway (:9000)
#   plus local PostgreSQL and RabbitMQ. See README "Setup & run locally".
#
# Covers:
#   Gateway <-> Inventory  (HTTP proxy: CRUD for every /api/movies endpoint)
#   Gateway <-> RabbitMQ <-> Billing (publish + order persisted in billing_db)
#
# Usage: ./scripts/test_local.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

set -a
# shellcheck disable=SC1091
source "$ROOT_DIR/.env"
set +a

GATEWAY_URL="${GATEWAY_URL:-http://localhost:${GATEWAY_PORT:-9000}}"

PASS=0
FAIL=0

check() {
  local desc="$1" got="$2" expected="$3"
  if [ "$got" = "$expected" ]; then
    PASS=$((PASS + 1))
    echo "PASS: $desc"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: $desc (expected '$expected', got '$got')"
  fi
}

echo "Preflight: checking API Gateway at $GATEWAY_URL ..."
if ! curl -s -o /dev/null "$GATEWAY_URL/health"; then
  echo "ERROR: API Gateway not reachable at $GATEWAY_URL"
  echo "Start the Inventory API, Billing API and API Gateway locally first (see README)."
  exit 1
fi

echo
echo "=== 1. Gateway health ==="
check "GET /health -> 200" "$(curl -s -o /dev/null -w '%{http_code}' "$GATEWAY_URL/health")" "200"

echo
echo "=== 2. Inventory CRUD via gateway (HTTP proxy) ==="
curl -s -o /dev/null -X DELETE "$GATEWAY_URL/api/movies"

check "POST /api/movies -> 201" \
  "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$GATEWAY_URL/api/movies" \
      -H 'Content-Type: application/json' -d '{"title": "Dune", "description": "Sci-fi epic"}')" "201"

check "GET /api/movies -> 200" \
  "$(curl -s -o /dev/null -w '%{http_code}' "$GATEWAY_URL/api/movies")" "200"

count="$(curl -s "$GATEWAY_URL/api/movies" | python3 -c 'import sys, json; print(len(json.load(sys.stdin)))')"
check "GET /api/movies returns 1 movie" "$count" "1"

check "GET /api/movies?title=Dune -> 200" \
  "$(curl -s -o /dev/null -w '%{http_code}' "$GATEWAY_URL/api/movies?title=Dune")" "200"

movie_id="$(curl -s "$GATEWAY_URL/api/movies" | python3 -c 'import sys, json; print(json.load(sys.stdin)[0]["id"])')"

check "GET /api/movies/$movie_id -> 200" \
  "$(curl -s -o /dev/null -w '%{http_code}' "$GATEWAY_URL/api/movies/$movie_id")" "200"

check "PUT /api/movies/$movie_id -> 200" \
  "$(curl -s -o /dev/null -w '%{http_code}' -X PUT "$GATEWAY_URL/api/movies/$movie_id" \
      -H 'Content-Type: application/json' -d '{"title": "Dune: Part Two"}')" "200"

check "DELETE /api/movies/$movie_id -> 200" \
  "$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$GATEWAY_URL/api/movies/$movie_id")" "200"

check "DELETE /api/movies (all) -> 200" \
  "$(curl -s -o /dev/null -w '%{http_code}' -X DELETE "$GATEWAY_URL/api/movies")" "200"

echo
echo "=== 3. Billing via gateway (RabbitMQ publish) ==="
resp="$(curl -s -w '\n%{http_code}' -X POST "$GATEWAY_URL/api/billing" \
    -H 'Content-Type: application/json' \
    -d '{"user_id": "3", "number_of_items": "5", "total_amount": "180"}')"
code="$(printf '%s' "$resp" | tail -n1)"
body="$(printf '%s' "$resp" | head -n -1)"

check "POST /api/billing -> 200" "$code" "200"

if echo "$body" | grep -q 'Message posted'; then
  PASS=$((PASS + 1))
  echo "PASS: gateway acknowledges 'Message posted'"
else
  FAIL=$((FAIL + 1))
  echo "FAIL: gateway did not acknowledge 'Message posted' (body: $body)"
fi

echo
echo "=== 4. Billing consumer -> billing_db (needs the consumer running) ==="
if command -v psql >/dev/null 2>&1; then
  rows="$(PGPASSWORD="${BILLING_DB_PASSWORD}" psql -h "${BILLING_DB_HOST}" -p "${BILLING_DB_PORT}" \
      -U "${BILLING_DB_USER}" -d "${BILLING_DB_NAME}" -tAc 'SELECT count(*) FROM orders;')"
  echo "INFO: orders rows now: ${rows} (expect >= 1 if the consumer processed the message)"
  if [ "${rows:-0}" -ge 1 ] 2>/dev/null; then
    PASS=$((PASS + 1))
    echo "PASS: order persisted in billing_db.orders"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL: no rows found in billing_db.orders (is the Billing consumer running?)"
  fi
else
  echo "SKIP: psql not available locally; check orders manually (see docs/billing-test-steps.md)"
fi

echo
echo "==== RESULT: $PASS passed, $FAIL failed ===="
[ "$FAIL" -eq 0 ]
