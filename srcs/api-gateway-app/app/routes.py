import requests
from flask import Blueprint, jsonify, request, current_app, Response
from app.publisher import publish_billing_message

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

    return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))


@bp.route("/api/billing", methods=["POST"])
def publish_billing():
    """Receive a billing request and publish it to billing_queue.
    Must succeed even if the Billing API consumer is not running --
    only the RabbitMQ broker needs to be up."""
    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    config = {
        "RABBITMQ_HOST": current_app.config["RABBITMQ_HOST"],
        "RABBITMQ_PORT": current_app.config["RABBITMQ_PORT"],
        "RABBITMQ_USER": current_app.config["RABBITMQ_USER"],
        "RABBITMQ_PASSWORD": current_app.config["RABBITMQ_PASSWORD"],
        "RABBITMQ_QUEUE": current_app.config["RABBITMQ_QUEUE"],
    }

    try:
        publish_billing_message(body, config)
    except Exception as exc:
        return jsonify({"error": f"Could not publish message: {exc}"}), 502

    return jsonify({"message": "Message posted"}), 200