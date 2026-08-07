import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()


def create_app():
    """Application factory for the API Gateway."""
    app = Flask(__name__)

    app.config["INVENTORY_API_HOST"] = os.getenv("INVENTORY_API_HOST", "localhost")
    app.config["INVENTORY_API_PORT"] = os.getenv("INVENTORY_API_PORT", "8080")
    app.config["RABBITMQ_HOST"] = os.getenv("RABBITMQ_HOST", "localhost")
    app.config["RABBITMQ_PORT"] = os.getenv("RABBITMQ_PORT", "5672")
    app.config["RABBITMQ_USER"] = os.getenv("RABBITMQ_USER", "")
    app.config["RABBITMQ_PASSWORD"] = os.getenv("RABBITMQ_PASSWORD", "")
    app.config["RABBITMQ_QUEUE"] = os.getenv("RABBITMQ_QUEUE", "billing_queue")

    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app