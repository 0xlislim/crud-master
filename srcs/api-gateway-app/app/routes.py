"""TODO implement:
- ANY /api/movies* -> forward request (method, body, query params) to
  INVENTORY_API_URL:INVENTORY_API_PORT/api/movies*, return response verbatim
- POST /api/billing -> publish request body as JSON message to billing_queue
  (must succeed even if Billing API consumer is not running, since RabbitMQ
  just needs the queue/broker up, not the consumer)
"""


"""Routes for API Gateway."""

import requests
from flask import Blueprint, jsonify, request, current_app, Response

bp = Blueprint("routes", __name__)


@bp.route("/health", methods=["GET"])
def health():
    """Basic health check so we can confirm the gateway skeleton is alive."""
    return jsonify({"status": "ok", "service": "api-gateway"}), 200


@bp.route("/api/movies", methods=["GET", "POST", "DELETE"])
@bp.route("/api/movies/<path:movie_id>", methods=["GET", "PUT", "DELETE"])
def proxy_movies(movie_id=None):
    """Forward any /api/movies* request to the Inventory API and return its
    response verbatim (status code, JSON body, query params, method, body)."""
    host = current_app.config["INVENTORY_API_HOST"]
    port = current_app.config["INVENTORY_API_PORT"]

    path = f"/api/movies/{movie_id}" if movie_id is not None else "/api/movies"
    url = f"http://{host}:{port}{path}"

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            params=request.args,
            json=request.get_json(silent=True),
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Inventory API is unreachable"}), 502

    # Return the Inventory API's response as-is (status + body + content type)
    return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))


# TODO (Task 12): POST /api/billing -> publish request body as JSON message to
#   billing_queue via app/publisher.py (must succeed even if Billing API is down)