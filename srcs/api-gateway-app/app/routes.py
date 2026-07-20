"""Routes for API Gateway.

TODO implement:
- ANY /api/movies* -> forward request (method, body, query params) to
  INVENTORY_API_URL:INVENTORY_API_PORT/api/movies*, return response verbatim
- POST /api/billing -> publish request body as JSON message to billing_queue
  (must succeed even if Billing API consumer is not running, since RabbitMQ
  just needs the queue/broker up, not the consumer)
"""
