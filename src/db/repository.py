"""
repository.py - Message persistence layer
All database operations are written in raw SQL using SQLAlchemy's text().
"""

import logging
from datetime import datetime
from sqlalchemy import text

from src.db.database import Database
from src.models.message import Message, MessageStatus

logger = logging.getLogger(__name__)


class MessageRepository:
    """
    Handles all database read/write operations for messages.
    """

    def __init__(self, db: Database):
        self._db = db

    async def save(self, message: Message):
        """
        Inserts a new message into the database with status Received.
        Called by the API Gateway upon receiving a new message.
        """
        async with self._db.connection() as conn:
            await conn.execute(text("""
                INSERT INTO messages (id, content, sender_name, sender_email, sender_phone,
                            destination, customer_type, status, retry_count, created_at)
                VALUES
                    (:id, :content, :sender_name, :sender_email, :sender_phone,
                     :destination, :customer_type, :status, :retry_count, :created_at)
            """), {
                "id": message.id,
                "content": message.content,
                "sender_name": message.sender.name,
                "sender_email": message.sender.email,
                "sender_phone": message.sender.phone,
                "destination": message.destination,
                "customer_type": message.customer_type,
                "status": MessageStatus.RECEIVED,
                "retry_count": message.retry_count,
                "created_at": message.created_at,
            })
            await conn.commit()
            logger.info(f"[{message.id}] Saved to DB with status Received")

    async def update_status(self, message_id, status: MessageStatus):
        """
        Updates the status of an existing message.
        Called at each stage of the processing pipeline.
        """
        async with self._db.connection() as conn:
            await conn.execute(text("""
                UPDATE messages
                SET status = :status, updated_at = :updated_at
                WHERE id = :id
            """), {
                "status": status,
                "updated_at": datetime.utcnow(),
                "id": message_id,
            })
            await conn.commit()
            logger.info(f"[{message_id}] Status updated to {status}")

    async def get_stuck_messages(self):
        """
        Returns all messages stuck in InProgress status.
        Used during startup recovery to detect messages interrupted by a crash.
        """
        async with self._db.connection() as conn:
            result = await conn.execute(text("""
                SELECT id FROM messages WHERE status = :status
            """), {"status": MessageStatus.IN_PROGRESS})
            return result.fetchall()

    async def reset_to_pending(self, message_id):
        """
        Resets a stuck InProgress message back to Pending.
        Allows the worker to pick it up again after recovery.
        """
        await self.update_status(message_id, MessageStatus.PENDING)
        logger.info(f"[{message_id}] Reset to Pending after recovery")
