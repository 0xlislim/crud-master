"""RabbitMQ consumer for Billing API.

TODO:
- connect to RabbitMQ using pika (host/user/pass from .env)
- declare/consume from billing_queue
- on_message callback:
    - parse JSON body {user_id, number_of_items, total_amount}
    - insert row into billing_db.orders
    - ack message
- ensure pending messages are processed on startup (basic_qos + consume loop covers this by default with a durable queue)
"""
