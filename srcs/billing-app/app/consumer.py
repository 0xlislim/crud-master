"""RabbitMQ consumer for Billing API."""
import os
import json
import signal
import time
import pika
from dotenv import load_dotenv
from app.models import init_db, Order

# Load environment variables
load_dotenv()

def start_consumer():
    # Load environment configuration
    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", 5672))
    user = os.getenv("RABBITMQ_USER", "")
    password = os.getenv("RABBITMQ_PASSWORD", "")
    queue = os.getenv("RABBITMQ_QUEUE", "billing_queue")
    
    # Initialize DB connection with retries (in case the database takes time to boot)
    print("Initializing Database Connection...")
    Session = None
    for attempt in range(10):
        try:
            Session = init_db()
            print("Successfully connected to the database!")
            break
        except Exception as e:
            print(f"Database connection attempt {attempt+1} failed: {e}. Retrying in 3 seconds...")
            time.sleep(3)
            
    if not Session:
        raise Exception("Failed to connect to billing database after multiple attempts.")
        
    # Set up RabbitMQ credentials and connection parameters
    credentials = pika.PlainCredentials(user, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    
    # Connect to RabbitMQ with retries (essential for startup coordination in VM/PM2 environment)
    connection = None
    print("Connecting to RabbitMQ...")
    for attempt in range(15):
        try:
            connection = pika.BlockingConnection(parameters)
            print("Successfully connected to RabbitMQ!")
            break
        except pika.exceptions.AMQPConnectionError as e:
            print(f"RabbitMQ connection attempt {attempt+1} failed: {e}. Retrying in 3 seconds...")
            time.sleep(3)
            
    if not connection:
        raise Exception("Failed to connect to RabbitMQ after multiple attempts.")
        
    channel = connection.channel()
    
    # Declare a durable queue to survive restarts / broker crashes
    channel.queue_declare(queue=queue, durable=True)
    
    # Apply basic_qos (prefetch_count=1) for fair message dispatching
    channel.basic_qos(prefetch_count=1)
    
    def callback(ch, method, properties, body):
        print(f"Received message: {body.decode()}")
        session = Session()
        try:
            data = json.loads(body.decode())
            
            # Extract and parse expected parameters from the JSON body
            # Ensure they are formatted correctly even if strings are passed
            user_id = int(data['user_id'])
            number_of_items = int(data['number_of_items'])
            total_amount = float(data['total_amount'])
            
            # Create order in billing_db
            new_order = Order(
                user_id=user_id,
                number_of_items=number_of_items,
                total_amount=total_amount
            )
            session.add(new_order)
            session.commit()
            print(f"Order created successfully: ID {new_order.id}, User {user_id}, Total {total_amount}")
            
            # Acknowledge the message upon successful database insert
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("Message acknowledged.")
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Discarding malformed message due to parsing error: {e}")
            # Acknowledge formatting/validation errors to avoid getting stuck in loops
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Temporary processing error: {e}. Requeuing message...")
            session.rollback()
            # Wait a moment to prevent tight loop retries before requeuing
            time.sleep(2)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            session.close()
            
    # Consume messages from billing_queue
    channel.basic_consume(queue=queue, on_message_callback=callback)
    
    print(f"Waiting for messages in '{queue}'... Press CTRL+C to exit.")

    def shutdown(signum, frame):
        print("Received shutdown signal, stopping consumer...")
        channel.stop_consuming()

    signal.signal(signal.SIGTERM, shutdown)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Stopping consumer...")
        channel.stop_consuming()
    finally:
        if connection.is_open:
            connection.close()
