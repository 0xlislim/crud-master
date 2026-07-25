"""Entrypoint: python server.py
Loads .env, starts RabbitMQ consumer loop.
"""
from app.consumer import start_consumer

if __name__ == "__main__":
    print("Starting Billing API (RabbitMQ Consumer)...")
    start_consumer()
