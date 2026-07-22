"""Entrypoint: python server.py
Loads .env, creates app via app factory, runs on configured host/port.
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("INVENTORY_API_HOST", "0.0.0.0")
    port = int(os.getenv("INVENTORY_API_PORT", 8080))
    # Binding to the environment variable ensures flexible network mapping
    app.run(host=host, port=port, debug=True)
