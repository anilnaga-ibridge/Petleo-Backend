# Kafka producer functionality (commented out for now)
# When Kafka is available, uncomment the code below:

# from kafka import KafkaProducer
# import json

# producer = KafkaProducer(
#     bootstrap_servers='localhost:9092',  
#     value_serializer=lambda v: json.dumps(v).encode('utf-8')
# )

def publish_user_created_event(user_data):
    """
    Publish user data to Kafka topic 'user_created'
    Currently disabled - enable when Kafka is set up
    """
    # When Kafka is available, uncomment:
    # producer.send('user_created', user_data)
    # producer.flush()
    
    # For now, just log the event
    print(f"User created event: {user_data}")
    pass


# orchestrator/kafka_publish.py
# # users/kafka_producer.py
# # users/kafka_producer.py
# from kafka import KafkaProducer
# import json
# import os

# KAFKA_SERVER = os.getenv("KAFKA_SERVER", "localhost:9092")
# producer = KafkaProducer(
#     bootstrap_servers=KAFKA_SERVER,
#     value_serializer=lambda v: json.dumps(v).encode("utf-8")
# )

# def send_user_created_event(payload):
#     """
#     Generic Kafka producer for multi-service registration
#     """
#     producer.send("user_created", value=payload)
#     producer.flush()


# # users/kafka_producer.py
# from kafka import KafkaProducer
# import json
# import os

# # Kafka configuration
# KAFKA_SERVER = os.getenv("KAFKA_SERVER", "localhost:9092")
# producer = KafkaProducer(
#     bootstrap_servers=KAFKA_SERVER,
#     value_serializer=lambda v: json.dumps(v).encode("utf-8")
# )

# def publish_user_created_event(user, extra_fields=None, role=None):
#     """
#     Publish a user_created event to Kafka.
#     This is generic and works for multiple services.
    
#     Args:
#         user: Django user instance
#         extra_fields: dict of additional fields (service-specific)
#         role: optional role string
#     """
#     payload = {
#         "auth_user_id": str(user.id),
#         "username": user.username,
#         "email": user.email,
#         "first_name": getattr(user, "first_name", ""),
#         "last_name": getattr(user, "last_name", ""),
#         "role": role or getattr(user, "role", "user")
#     }

#     if extra_fields:
#         payload.update(extra_fields)

#     producer.send("user_created", value=payload)
#     producer.flush()



# # auth_producer.py
# from kafka import KafkaProducer
# import json
# from django.contrib.auth import get_user_model
# from rest_framework_simplejwt.tokens import RefreshToken
# import os
# import django

# # Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
# django.setup()

# User = get_user_model()

# # Initialize Kafka producer
# producer = KafkaProducer(
#     bootstrap_servers='localhost:9092',
#     value_serializer=lambda v: json.dumps(v).encode('utf-8')
# )

# def publish_user_created_event(user, extra_fields=None, role=None):
#     """
#     Publishes a Kafka event for a newly created user.
#     - user: Django User instance
#     - extra_fields: dict of additional data sent by microservices
#     - role: optional role string
#     """
#     payload = {
#         "auth_user_id": str(user.id),
#         "email": user.email,
#         "role": role or getattr(user, "role", "user"),
#         "extra_fields": extra_fields or {}
#     }

#     producer.send('user_created', payload)
#     producer.flush()


# def register_user(data):
#     """
#     Centralized user registration.
#     Handles auth creation + JWT + broadcasting full payload.
#     - data: dict from request, can contain arbitrary extra fields
#     """
#     # Extract core auth fields
#     username = data["username"]
#     password = data["password"]
#     email = data["email"]
#     role = data.get("role", "user")

#     # Create user in Auth service
#     user = User.objects.create_user(
#         username=username,
#         password=password,
#         email=email,
#         role=role
#     )

#     # Generate JWT token
#     token = str(RefreshToken.for_user(user).access_token)

#     # Separate extra fields (everything except username, email, password, role)
#     extra_fields = {k: v for k, v in data.items() if k not in ["username", "email", "password", "role"]}

#     # Publish Kafka message for other services to consume
#     publish_user_created_event(user, extra_fields=extra_fields, role=role)

#     # Return auth info + full payload
#     response = {
#         "message": "User registered successfully",
#         "auth_user_id": str(user.id),
#         "jwt": token,
#         "payload": data
#     }
#     return response

# # auth_producer.py
# from kafka import KafkaProducer
# import json
# from django.contrib.auth import get_user_model
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.core.mail import send_mail
# from django.conf import settings
# import os
# import django
# import string
# import random

# # Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
# django.setup()

# User = get_user_model()

# # Initialize Kafka producer
# producer = KafkaProducer(
#     bootstrap_servers='localhost:9092',
#     value_serializer=lambda v: json.dumps(v).encode('utf-8')
# )

# def generate_random_password(length=12):
#     """
#     Generates a random password with letters, digits, and symbols.
#     """
#     chars = string.ascii_letters + string.digits + string.punctuation
#     return ''.join(random.choice(chars) for _ in range(length))

# def send_password_email(to_email, password, username):
#     """
#     Send an email to the newly created user with their credentials.
#     """
#     subject = "Your Account Credentials"
#     message = f"""
# Hi {username},

# Your account has been created successfully.

# Username: {username}
# Password: {password}

# Please log in and change your password immediately for security.

# Regards,
# Admin Team
# """
#     send_mail(
#         subject,
#         message,
#         settings.DEFAULT_FROM_EMAIL,
#         [to_email],
#         fail_silently=False,
#     )

# def publish_user_created_event(user, extra_fields=None, role=None):
#     """
#     Publishes a Kafka event for a newly created user.
#     - user: Django User instance
#     - extra_fields: dict of additional data sent by microservices
#     - role: optional role string
#     """
#     payload = {
#         "auth_user_id": str(user.id),
#         "email": user.email,
#         "role": role or getattr(user, "role", "user"),
#         "extra_fields": extra_fields or {}
#     }

#     producer.send('user_created', payload)
#     producer.flush()


# def register_user(data, created_by_superadmin=False):
#     """
#     Centralized user registration.
#     Handles auth creation + JWT + broadcasting full payload.
#     - data: dict from request, can contain arbitrary extra fields
#     - created_by_superadmin: bool, if True generates random password and sends email
#     """
#     username = data["username"]
#     email = data["email"]
#     role = data.get("role", "user")

#     # Decide password
#     if created_by_superadmin:
#         password = generate_random_password()
#         send_password_email(email, password, username)
#     else:
#         password = data["password"]

#     # Create user in Auth service
#     user = User.objects.create_user(
#         username=username,
#         password=password,
#         email=email,
#         role=role
#     )

#     # Generate JWT token
#     token = str(RefreshToken.for_user(user).access_token)

#     # Separate extra fields (everything except username, email, password, role)
#     extra_fields = {k: v for k, v in data.items() if k not in ["username", "email", "password", "role"]}

#     # Publish Kafka message for other services
#     publish_user_created_event(user, extra_fields=extra_fields, role=role)

#     # Return auth info + full payload
#     response = {
#         "message": "User registered successfully",
#         "auth_user_id": str(user.id),
#         "jwt": token,
#         "payload": data
#     }
#     return response
# import os
# import django
# import string
# import random
# import json
# import threading
# from kafka import KafkaProducer
# from django.contrib.auth import get_user_model
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.core.mail import send_mail
# from django.conf import settings
# from kafka.errors import KafkaError

# # Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
# django.setup()

# User = get_user_model()

# # Singleton Kafka producer
# class KafkaProducerSingleton:
#     _instance = None

#     @classmethod
#     def get_instance(cls):
#         if cls._instance is None:
#             cls._instance = KafkaProducer(
#                 bootstrap_servers='localhost:9092',
#                 value_serializer=lambda v: json.dumps(v).encode('utf-8')
#             )
#         return cls._instance

# producer = KafkaProducerSingleton.get_instance()

# # Utilities
# def generate_random_password(length=12):
#     chars = string.ascii_letters + string.digits + string.punctuation
#     return ''.join(random.choice(chars) for _ in range(length))

# def send_email_async(subject, message, recipient_list):
#     """Send email in a separate thread to avoid blocking."""
#     def _send():
#         try:
#             send_mail(
#                 subject,
#                 message,
#                 settings.DEFAULT_FROM_EMAIL,
#                 recipient_list,
#                 fail_silently=False
#             )
#         except Exception as e:
#             print(f"Error sending email: {e}")
#     threading.Thread(target=_send).start()

# def send_password_email(to_email, password, username):
#     subject = "Your Account Credentials"
#     message = f"""
# Hi {username},

# Your account has been created successfully.

# Username: {username}
# Password: {password}

# Please log in and change your password immediately for security.

# Regards,
# Admin Team
# """
#     send_email_async(subject, message, [to_email])

# def publish_user_created_event(user, extra_fields=None, role=None):
#     payload = {
#         "auth_user_id": str(user.id),
#         "email": user.email,
#         "role": role or getattr(user, "role", "user"),
#         "extra_fields": extra_fields or {}
#     }
#     try:
#         future = producer.send('user_created', payload)
#         result = future.get(timeout=10)
#         print(f"✅ Message sent to Kafka: {payload}")
#     except KafkaError as e:
#         print(f"Kafka error: {e}")

# # Registration function
# def register_user(data):
#     username = data["username"]
#     email = data["email"]
#     role = data.get("role", "user")
#     password = data.get("password")

#     # Generate password if missing
#     generated_password = None
#     if not password:
#         password = generate_random_password()
#         generated_password = password
#         send_password_email(email, password, username)

#     # Create user
#     user = User.objects.create_user(
#         username=username,
#         password=password,
#         email=email,
#         role=role
#     )

#     # Generate JWT
#     token = str(RefreshToken.for_user(user).access_token)

#     # Extra fields
#     extra_fields = {
#         k: v for k, v in data.items() 
#         if k not in ["username", "email", "password", "role"]
#     }

#     # Publish Kafka event
#     publish_user_created_event(user, extra_fields=extra_fields, role=role)

#     response = {
#         "message": "User registered successfully.",
#         "user": {
#             "auth_user_id": str(user.id),
#             "username": user.username,
#             "email": user.email,
#             "role": role
#         },
#         "jwt": token
#     }
#     return response


# import os
# import django
# import string
# import random
# import json
# import threading
# from kafka import KafkaProducer
# from django.contrib.auth import get_user_model
# from rest_framework_simplejwt.tokens import RefreshToken
# from django.core.mail import send_mail
# from django.conf import settings
# from kafka.errors import KafkaError

# # Setup Django environment
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
# django.setup()

# User = get_user_model()

# # Singleton Kafka producer
# class KafkaProducerSingleton:
#     _instance = None

#     @classmethod
#     def get_instance(cls):
#         if cls._instance is None:
#             cls._instance = KafkaProducer(
#                 bootstrap_servers='localhost:9092',
#                 value_serializer=lambda v: json.dumps(v).encode('utf-8')
#             )
#         return cls._instance

# producer = KafkaProducerSingleton.get_instance()

# # Utilities
# def generate_random_password(length=12):
#     chars = string.ascii_letters + string.digits + string.punctuation
#     return ''.join(random.choice(chars) for _ in range(length))

# def send_email_async(subject, message, recipient_list):
#     """Send email in a separate thread to avoid blocking."""
#     def _send():
#         try:
#             send_mail(
#                 subject,
#                 message,
#                 settings.DEFAULT_FROM_EMAIL,
#                 recipient_list,
#                 fail_silently=False
#             )
#             print(f"✅ Email sent to {recipient_list}")
#         except Exception as e:
#             print(f"❌ Error sending email to {recipient_list}: {e}")
#     threading.Thread(target=_send).start()

# def send_password_email(to_email, password, username):
#     subject = "Your Account Credentials"
#     message = f"""
# Hi {username},

# Your account has been created successfully.

# Username: {username}
# Password: {password}

# Please log in and change your password immediately for security.

# Regards,
# Admin Team
# """
#     send_email_async(subject, message, [to_email])

# def publish_user_created_event(user, extra_fields=None, role=None):
#     payload = {
#         "auth_user_id": str(user.id),
#         "email": user.email,
#         "role": role or getattr(user, "role", "user"),
#         "extra_fields": extra_fields or {}
#     }
#     try:
#         future = producer.send('user_created', payload)
#         result = future.get(timeout=10)  # Wait for Kafka ack
#         print(f"✅ Message sent to Kafka: {payload}")
#     except KafkaError as e:
#         print(f"❌ Kafka error: {e}")

# # Registration function
# def register_user(data):
#     username = data.get("username")
#     email = data.get("email")
#     role = data.get("role", "user")
#     password = data.get("password")

#     # Generate password if missing or empty
#     generated_password = None
#     if not password:
#         password = generate_random_password()
#         generated_password = password
#         print(f"Generated password for {email}: {password}")
#         send_password_email(email, password, username)

#     # Create user
#     user = User.objects.create_user(
#         username=username,
#         password=password,
#         email=email,
#         role=role
#     )

#     # Generate JWT
#     token = str(RefreshToken.for_user(user).access_token)

#     # Extra fields
#     extra_fields = {
#         k: v for k, v in data.items() if k not in ["username", "email", "password", "role"]
#     }

#     # Publish Kafka event
#     publish_user_created_event(user, extra_fields=extra_fields, role=role)

#     response = {
#         "message": "User registered successfully.",
#         "user": {
#             "auth_user_id": str(user.id),
#             "username": user.username,
#             "email": user.email,
#             "role": role
#         },
#         "jwt": token
#     }

#     # Include generated password in response for dev/testing (remove in production)
#     if generated_password:
#         response["generated_password"] = generated_password

#     return response
# ===============================saterday===================================

# import os, django, string, random, json, threading
# from kafka import KafkaProducer
# from django.core.mail import send_mail
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from rest_framework_simplejwt.tokens import RefreshToken

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auth_service.settings")
# django.setup()
# User = get_user_model()

# # Initialize producer lazily to avoid connection errors on import
# producer = None

# def get_kafka_producer():
#     """Get Kafka producer instance, creating it if needed"""
#     global producer
#     if producer is None:
#         try:
#             producer = KafkaProducer(
#                 bootstrap_servers='localhost:9092',
#                 value_serializer=lambda v: json.dumps(v).encode('utf-8')
#             )
#         except Exception as e:
#             print(f"Warning: Kafka producer initialization failed: {e}")
#             producer = None
#     return producer

# def generate_random_password(length=12):
#     chars = string.ascii_letters + string.digits + string.punctuation
#     return ''.join(random.choice(chars) for _ in range(length))

# def send_email_async(subject, message, recipients):
#     def _send(): send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients)
#     threading.Thread(target=_send).start()

# def publish_user_created_event(user, extra_fields=None, role=None):
#     payload = {
#         'auth_user_id': str(user.id),
#         'email': user.email,
#         'role': role or getattr(user, 'role', 'user'),
#         'extra_fields': extra_fields or {}
#     }
    
#     # Get producer instance (lazy initialization)
#     kafka_producer = get_kafka_producer()
#     if kafka_producer:
#         try:
#             kafka_producer.send('user_created', payload)
#         except Exception as e:
#             print(f"Warning: Failed to send Kafka message: {e}")
#     else:
#         print("Warning: Kafka producer not available, skipping event publishing")



# ==============================phno otp ====================================
# auth_service/kafka_producer.py
# users/kafka_producer.py
# import json
# import threading
# from kafka import KafkaProducer
# from django.conf import settings

# _producer = None
# _kafka_servers = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', ['localhost:9092'])

# def get_kafka_producer():
#     global _producer
#     if _producer is None:
#         try:
#             _producer = KafkaProducer(
#                 bootstrap_servers=_kafka_servers,
#                 value_serializer=lambda v: json.dumps(v).encode('utf-8'),
#                 linger_ms=5,
#                 retries=5
#             )
#         except Exception as e:
#             print("Kafka producer init failed:", e)
#             _producer = None
#     return _producer

# def publish_user_created_event(payload: dict, topic: str='user_created'):
#     producer = get_kafka_producer()
#     if not producer:
#         print("Kafka unavailable — skipping publish", payload)
#         return False
#     try:
#         producer.send(topic, payload)
#         # fire-and-forget; flush in a thread optionally
#         return True
#     except Exception as e:
#         print("Kafka publish failed:", e)
#         return False
# # kafka_producer.py

# # Kafka producer setup
# producer = KafkaProducer(
#     bootstrap_servers=['localhost:9092'],  # Replace with your Kafka broker address
#     value_serializer=lambda v: json.dumps(v).encode('utf-8')
# )

# def publish_user_event(event_type, user_data):
#     """
#     Sends user events to Kafka topic 'user_events'
#     event_type: like 'USER_REGISTERED' or 'USER_VERIFIED'
#     user_data: dict with user info (id, email, role, etc.)
#     """
#     message = {
#         "event": event_type,
#         "data": user_data
#     }

#     # Publish to Kafka topic
#     producer.send('user_events', message)
#     producer.flush()
#     print(f"✅ Sent {event_type} event to Kafka:", message)
# import json
# from kafka import KafkaProducer
# from kafka.errors import KafkaError

# # Kafka configuration
# KAFKA_BROKER_URL = "localhost:9092"
# USER_TOPIC = "user_events"

# print("🚀 Initializing Kafka Producer...")
# print(f"🔗 Connecting to Kafka broker at: {KAFKA_BROKER_URL}")

# try:
#     # Create Kafka producer
#     producer = KafkaProducer(
#         bootstrap_servers=[KAFKA_BROKER_URL],
#         value_serializer=lambda v: json.dumps(v).encode("utf-8"),
#         acks="all",
#         retries=3
#     )
#     print("✅ Kafka Producer created successfully!")
# except Exception as e:
#     print("❌ Failed to connect to Kafka broker.")
#     print(f"Error: {e}")
#     raise SystemExit

# def publish_user_event(event_type, user_data):
#     """
#     Send user-related event to Kafka.
#     event_type: 'USER_CREATED' or 'USER_VERIFIED', etc.
#     user_data: dict with user info like id, role, permissions.
#     """
#     print(f"\n📦 Preparing to send event: {event_type}")
#     print(f"🧾 Event Data: {user_data}")

#     try:
#         event = {
#             "event_type": event_type,
#             "data": user_data
#         }
#         print(f"📤 Sending event to topic '{USER_TOPIC}'...")
#         producer.send(USER_TOPIC, value=event)
#         producer.flush()
#         print(f"✅ Successfully sent {event_type} event to Kafka!")
#     except KafkaError as e:
#         print(f"❌ Kafka error while sending {event_type}: {e}")
#     except Exception as e:
#         print(f"⚠️ Unexpected error while sending {event_type}: {e}")

# # --- Test the producer ---
# if __name__ == "__main__":
#     test_data = {
#         "id": 1,
#         "email": "admin@example.com",
#         "role": "ADMIN"
#     }
#     publish_user_event("USER_CREATED", test_data)
# kafka_producer.py
# import json
# import logging
# from kafka import KafkaProducer
# from kafka.errors import KafkaError
# from django.conf import settings

# logger = logging.getLogger(__name__)

# # -----------------------------
# # Global Kafka Configuration
# # -----------------------------
# KAFKA_BROKER_URL = getattr(settings, "KAFKA_BROKER_URL", "localhost:9092")
# DEFAULT_TOPIC = getattr(settings, "KAFKA_EVENT_TOPIC", "service_events")
# SERVICE_NAME = getattr(settings, "SERVICE_NAME", None)

# if not SERVICE_NAME:
#     raise ValueError(
#         "❌ Missing SERVICE_NAME in Django settings. Example: SERVICE_NAME = 'auth_service'"
#     )

# logger.info(f"🚀 Initializing Kafka Producer for service: {SERVICE_NAME}")
# logger.info(f"🔗 Connecting to Kafka broker at: {KAFKA_BROKER_URL}")

# # -----------------------------
# # Initialize Kafka Producer
# # -----------------------------
# try:
#     producer = KafkaProducer(
#         bootstrap_servers=[KAFKA_BROKER_URL],
#         value_serializer=lambda v: json.dumps(v).encode("utf-8"),
#         acks="all",
#         retries=3,
#     )
#     logger.info("✅ Kafka Producer created successfully!")
# except Exception as e:
#     logger.error(f"❌ Failed to connect to Kafka broker ({KAFKA_BROKER_URL}) — {e}")
#     producer = None  # Prevent crashing the app
#     # You can optionally retry later or log metrics

# # -----------------------------
# # Publish Event Function
# # -----------------------------
# def publish_event(event_type: str, data: dict, topic: str = DEFAULT_TOPIC):
#     """
#     Generic Kafka event publisher used across microservices.
#     Every event includes:
#         - service (which service sent it)
#         - event_type
#         - data (payload)
#     """
#     if not event_type or not isinstance(data, dict):
#         logger.warning("⚠️ Invalid Kafka event: missing event_type or data.")
#         return

#     if not producer:
#         logger.warning("⚠️ Kafka Producer is not initialized. Skipping event publish.")
#         return

#     event = {
#         "service": SERVICE_NAME,
#         "event_type": event_type,
#         "data": data,
#     }

#     try:
#         logger.info(f"📤 Sending event '{event_type}' from {SERVICE_NAME} → topic '{topic}'...")
#         producer.send(topic, value=event)
#         producer.flush()
#         logger.info(f"✅ Successfully sent '{event_type}' to Kafka.")
#     except KafkaError as e:
#         logger.error(f"❌ Kafka error while sending {event_type}: {e}")
#     except Exception as e:
#         logger.exception(f"⚠️ Unexpected error while sending {event_type}: {e}")
import json
import logging
import time
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from django.conf import settings

logger = logging.getLogger(__name__)

# -----------------------------
# Global Kafka Configuration
# -----------------------------
KAFKA_BROKER_URL = getattr(settings, "KAFKA_BROKER_URL", "localhost:9092")
DEFAULT_TOPIC = getattr(settings, "KAFKA_EVENT_TOPIC", "service_events")
SERVICE_NAME = getattr(settings, "SERVICE_NAME", None)

if not SERVICE_NAME:
    raise ValueError("❌ Missing SERVICE_NAME in Django settings. Example: SERVICE_NAME = 'auth_service'")

logger.info(f"🚀 Initializing Kafka Producer for service: {SERVICE_NAME}")
logger.info(f"🔗 Connecting to Kafka broker at: {KAFKA_BROKER_URL}")

# -----------------------------
# Initialize Kafka Producer
# -----------------------------
producer = None
for attempt in range(3):  # try 3 times to connect
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER_URL],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=3,
        )
        logger.info("✅ Connected to Kafka broker successfully!")
        break
    except NoBrokersAvailable:
        logger.warning(f"⚠️ Attempt {attempt+1}/3 — Kafka broker not available at {KAFKA_BROKER_URL}. Retrying in 5s...")
        time.sleep(5)
    except Exception as e:
        logger.error(f"❌ Unexpected error while initializing Kafka Producer: {e}")
        break

if not producer:
    logger.error(f"❌ Failed to connect to Kafka after 3 attempts — proceeding without Kafka connection.")

# -----------------------------
# Publish Event Function
# -----------------------------
def publish_event(event_type: str, data: dict, topic: str = DEFAULT_TOPIC):
    """
    Generic Kafka event publisher used across microservices.
    Every event includes:
        - service (which service sent it)
        - event_type
        - data (payload)
    """
    if not event_type or not isinstance(data, dict):
        logger.warning("⚠️ Invalid Kafka event: missing event_type or data.")
        return

    if not producer:
        logger.warning("⚠️ Kafka Producer not initialized. Skipping event publish.")
        return

    event = {
        "service": SERVICE_NAME,
        "event_type": event_type,
        "data": data,
    }

    try:
        logger.info(f"📤 Sending event '{event_type}' from {SERVICE_NAME} → topic '{topic}'...")
        future = producer.send(topic, value=event)
        future.get(timeout=10)  # block to ensure delivery
        logger.info(f"✅ Successfully sent '{event_type}' to Kafka topic '{topic}'.")
    except KafkaError as e:
        logger.error(f"❌ Kafka error while sending {event_type}: {e}")
    except Exception as e:
        logger.exception(f"⚠️ Unexpected error while sending {event_type}: {e}")
