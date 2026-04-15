"""
config.py - Application configuration
Loads all settings from environment variables (.env file).
"""

import os
from dotenv import load_dotenv

load_dotenv()


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
VIP_QUEUE = os.getenv("VIP_QUEUE", "vip_queue")
REGULAR_QUEUE = os.getenv("REGULAR_QUEUE", "regular_queue")
DLQ_QUEUE = os.getenv("DLQ_QUEUE", "dead_letter_queue")


DB_URL = os.getenv("DB_URL", "postgresql+asyncpg://user:password@localhost/messaging_db")

MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "5"))  # Max parallel messages (X)
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


SERVICE_URL = os.getenv("SENDING_SERVICE_URL", "https://external-service/send")
TIMEOUT = float(os.getenv("SENDING_TIMEOUT", "10.0"))

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
FROM_PHONE = os.getenv("TWILIO_FROM_PHONE", "")

API_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@messaging.com")
