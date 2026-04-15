"""
main.py - Application entry point
Performs startup recovery, wires all dependencies, and starts the worker.
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import config
from src.db.database import Database
from src.db.repository import MessageRepository
from src.services.validation import ValidationService
from src.services.sending import SendingService
from src.services.notification import NotificationService
from src.services.worker import WorkerService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_services(db):
    """
    Wires all dependencies together and returns a ready WorkerService.
    All services are instantiated once and shared for the process lifetime.
    """
    repo = MessageRepository(db)
    validator = ValidationService()
    sender = SendingService(service_url=config.SERVICE_URL, timeout=config.TIMEOUT)
    notifier = NotificationService(
        twilio_sid=config.ACCOUNT_SID,
        twilio_token=config.AUTH_TOKEN,
        twilio_from=config.FROM_PHONE,
        sendgrid_key=config.API_KEY,
        sendgrid_from=config.FROM_EMAIL,
    )
    return WorkerService(repo, validator, sender, notifier)


async def recover(repo):
    """
    Startup recovery: finds messages stuck in InProgress (due to a crash)
    and resets them to Pending so the worker can reprocess them.
    """
    stuck = await repo.get_stuck_messages()
    if not stuck:
        logger.info("Recovery: no stuck messages found")
        return

    logger.warning(f"Recovery: resetting {len(stuck)} stuck message(s) to Pending")
    for record in stuck:
        await repo.reset_to_pending(record.id)


async def main():
    """
    Application startup sequence:
        1. Connect to the database
        2. Run recovery for interrupted messages
        3. Start the worker
    """
    logger.info("Messaging system starting...")

    db = Database(config.DB_URL)
    await db.create_tables()
    repo = MessageRepository(db)

    await recover(repo)

    worker = build_services(db)

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
