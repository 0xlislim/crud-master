"""TODO implement:
- ANY /api/movies* -> forward request (method, body, query params) to
  INVENTORY_API_URL:INVENTORY_API_PORT/api/movies*, return response verbatim
- POST /api/billing -> publish request body as JSON message to billing_queue
  (must succeed even if Billing API consumer is not running, since RabbitMQ
  just needs the queue/broker up, not the consumer)
"""


"""Routes for API Gateway."""

from flask import Blueprint, jsonify

bp = Blueprint("routes", __name__)


@bp.route("/health", methods=["GET"])
def health():
    """Basic health check so we can confirm the gateway skeleton is alive."""
    return jsonify({"status": "ok", "service": "api-gateway"}), 200


# TODO (Task 11): ANY /api/movies* -> forward request (method, body, query params)
#   to INVENTORY_API_HOST:INVENTORY_API_PORT/api/movies*, return response verbatim

# TODO (Task 12): POST /api/billing -> publish request body as JSON message to
#   billing_queue via app/publisher.py (must succeed even if Billing API is down)