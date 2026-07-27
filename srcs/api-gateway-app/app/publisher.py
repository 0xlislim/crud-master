"""RabbitMQ publisher helper for API Gateway."""

import json
import pika


def publish_billing_message(message: dict, config: dict) -> None:
    """Publish a JSON message to the billing_queue.

    Connects, declares the queue as durable (so messages survive a broker
    restart), publishes the message, and closes the connection. This must
    succeed even if the Billing API consumer is not currently running --
    it only depends on the RabbitMQ broker being up.
    """
    credentials = pika.PlainCredentials(config["RABBITMQ_USER"], config["RABBITMQ_PASSWORD"])
    parameters = pika.ConnectionParameters(
        host=config["RABBITMQ_HOST"],
        port=int(config["RABBITMQ_PORT"]),
        credentials=credentials,
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue=config["RABBITMQ_QUEUE"], durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=config["RABBITMQ_QUEUE"],
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
            content_type="application/json",
        ),
    )

    connection.close()