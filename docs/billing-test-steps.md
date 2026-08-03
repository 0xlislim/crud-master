# Billing API — Test Steps

These scenarios verify the asynchronous, queue-based behaviour of the Billing
API and its resilience when the consumer is down.

## Components under test

- **API Gateway** (`POST /api/billing`) — publishes the JSON body to RabbitMQ's
  `billing_queue`. Only needs the broker, not the Billing API, to be up.
- **RabbitMQ** — `billing_queue` (durable, so messages survive broker restarts).
- **Billing API** — consumes messages from `billing_queue`, inserts a row into
  `billing_db.orders`, then acknowledges the message.
- **PostgreSQL** — `billing_db.orders` table.

## Sample message

```json
{
  "user_id": "3",
  "number_of_items": "5",
  "total_amount": "180"
}
```

## Ways to publish a message

1. **Via the API Gateway** (requires gateway + RabbitMQ up):

   ```bash
   curl -X POST http://localhost:9000/api/billing \
        -H "Content-Type: application/json" \
        -d '{"user_id": "3", "number_of_items": "5", "total_amount": "180"}'
   ```

2. **Directly to RabbitMQ** using the management UI (http://localhost:15672,
   user/password from `.env` — `RABBITMQ_USER` / `RABBITMQ_PASSWORD`; `guest`
   only works from loopback and only if the credentials are still `guest`):
   `Queues` → `billing_queue` → `Publish message` with the JSON body above.

3. **Directly to RabbitMQ** using a small Python publisher:

   ```bash
   cd srcs/api-gateway-app && ./venv/bin/python - <<'EOF'
   import json, pika, os
   from dotenv import load_dotenv
   load_dotenv("../../.env")
   params = pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST", "localhost"),
                                      port=int(os.getenv("RABBITMQ_PORT", "5672")),
                                      credentials=pika.PlainCredentials(os.getenv("RABBITMQ_USER"), os.getenv("RABBITMQ_PASSWORD")))
   conn = pika.BlockingConnection(params)
   ch = conn.channel()
   ch.queue_declare(queue=os.getenv("RABBITMQ_QUEUE", "billing_queue"), durable=True)
   ch.basic_publish(exchange="", routing_key=os.getenv("RABBITMQ_QUEUE", "billing_queue"),
                    body=json.dumps({"user_id": "3", "number_of_items": "5", "total_amount": "180"}),
                    properties=pika.BasicProperties(delivery_mode=2))
   conn.close()
   EOF
   ```

## Checking the orders table

On the machine hosting the Billing API's PostgreSQL:

```bash
sudo -u postgres psql -d billing_db -c "SELECT * FROM orders ORDER BY id;"
```

> Note: `total_amount` is parsed from string input as a float and stored as
> `NUMERIC`. Use the exact expected values (e.g. `180`) when comparing.

## Scenario A — Normal processing

1. Start RabbitMQ, the Billing API, and the API Gateway.
2. Publish a message using any of the methods above.
3. Expected: the gateway returns `200 {"message": "Message posted"}`.
4. Check `orders` — a new row appears **immediately** with the parsed values.

## Scenario B — Billing API stopped (queue keeps messages)

1. Stop the Billing API:

   ```bash
   sudo pm2 stop billing-app          # in the VM
   # or CTRL+C if running python server.py locally
   ```

2. Publish several messages via the gateway.
3. Expected:
   - Every `POST /api/billing` still returns `200 {"message": "Message posted"}`.
   - The `orders` table is **not** updated (no new rows).
4. Confirm the messages are sitting in the queue:
   RabbitMQ UI `billing_queue` message count > 0 (unacked = 0), or via CLI:
   `sudo rabbitmqctl list_queues name messages messages_unacknowledged`.

## Scenario C — Billing API restarted (pending messages processed)

1. Start the Billing API again:

   ```bash
   sudo pm2 start billing-app         # in the VM
   ```

2. On startup the consumer connects to the broker and begins consuming.
3. Expected: all messages published while it was stopped are processed:
   - Every queued message is acknowledged (`messages` / `messages_unacknowledged`
     drop to 0).
   - One row per message appears in `orders`, in delivery order.

## Scenario D — Billing API restarted while RabbitMQ is down (startup retry)

Optional resilience check: the consumer retries the broker connection for up to
~15 attempts (3s apart) before giving up. Stop RabbitMQ, start the Billing API
— it logs retry attempts and, if RabbitMQ comes back within the window, connects
and drains any pending messages.

## Acceptance criteria (from the exercise)

- [ ] Publishing while the Billing API runs produces rows immediately.
- [ ] Publishing while the Billing API is stopped still succeeds at the gateway,
      and `orders` is not updated.
- [ ] Restarting the Billing API processes the pending messages and updates
      `orders`.
