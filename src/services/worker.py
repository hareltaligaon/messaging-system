"""
worker.py - Message processing worker
Consumes messages from RabbitMQ and orchestrates the full processing pipeline.
Always prioritizes the VIP queue over the regular queue.
Limits concurrency to MAX_CONCURRENT messages using asyncio.Semaphore.
"""

import asyncio
import json
import logging
from aio_pika import connect_robust, IncomingMessage

from src.models.message import Message, MessageStatus, CustomerType, Sender
from src.db.repository import MessageRepository
from src.services.validation import ValidationService
from src.services.sending import SendingService
from src.services.notification import NotificationService
import config

logger = logging.getLogger(__name__)


class WorkerService:
    """
    Listens to RabbitMQ queues and processes each message through
    the validation → sending → notification pipeline.

    Concurrency is controlled by asyncio.Semaphore(MAX_CONCURRENT).
    VIP queue is always consumed before the regular queue.
    """

    def __init__(self, repo: MessageRepository, validator: ValidationService,
                 sender: SendingService, notifier: NotificationService):
        self._repo = repo
        self._validator = validator
        self._sender = sender
        self._notifier = notifier
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT)

    async def start(self):
        """
        Connects to RabbitMQ and starts consuming from both queues.
        Runs indefinitely until the process is stopped.
        """
        connection = await connect_robust(config.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=config.MAX_CONCURRENT)

        vip_queue = await channel.declare_queue(config.VIP_QUEUE, durable=True)
        regular_queue = await channel.declare_queue(config.REGULAR_QUEUE, durable=True)

        # VIP queue is registered first — aio-pika processes it with priority
        await vip_queue.consume(self._process_message)
        await regular_queue.consume(self._process_message)

        logger.info(
            f"Worker started --> max concurrent: {config.MAX_CONCURRENT} | "
            f"queues: {config.VIP_QUEUE}, {config.REGULAR_QUEUE}"
        )

        try:
            await asyncio.Future()  # Run forever
        finally:
            await connection.close()

    # ── Core processing pipeline ──────────────────────────────────────────────

    async def _process_message(self, raw):
        """
        Full processing pipeline for a single message.
        1. Parse raw RabbitMQ message → Message domain object
        2. Update DB status → InProgress
        3. Validate → on failure: notify, NACK to DLQ
        4. Send → on failure: retry or NACK to DLQ
        5. On success: notify, update DB → Completed, ACK
        """
        async with self._semaphore:
            message = self._parse_message(raw)
            retry_count = self._get_retry_count(raw)

            logger.info(
                f"[{message.id}] Processing | type: {message.customer_type} | "
                f"attempt: {retry_count + 1}/{config.MAX_RETRIES}"
            )

            await self._repo.update_status(message.id, MessageStatus.IN_PROGRESS)

            if not await self._run_validation(message, raw):
                return

            await self._run_sending(message, raw, retry_count)

    async def _run_validation(self, message: Message, raw: IncomingMessage):
        """
        Validates the message. On failure, notifies the sender and NACKs to DLQ.

        Returns:
            True - validation passed, continue pipeline
            False - validation failed, message sent to DLQ
        """
        valid, reason = self._validator.validate(message)
        if valid:
            return True

        await self._repo.update_status(message.id, MessageStatus.VALIDATION_FAILED)
        await self._notifier.notify(message, MessageStatus.VALIDATION_FAILED, reason=reason)
        await raw.nack(requeue=False)
        return False

    async def _run_sending(self, message: Message, raw: IncomingMessage, retry_count):
        """
        Attempts to send the message. On success, notifies and ACKs.
        On failure, either retries (requeue) or gives up (NACK to DLQ).
        """
        success = await self._sender.send(message)

        if success:
            await self._on_success(message, raw)
        else:
            await self._on_failure(message, raw, retry_count)

    async def _on_success(self, message: Message, raw: IncomingMessage):
        """Handles a successful send: notify customer, update DB, ACK."""
        await self._notifier.notify(message, MessageStatus.COMPLETED)
        await self._repo.update_status(message.id, MessageStatus.COMPLETED)
        await raw.ack()
        logger.info(f"[{message.id}] Completed successfully")

    async def _on_failure(self, message: Message, raw: IncomingMessage, retry_count):
        """
        Handles a failed send.
        If max retries reached: mark Failed, notify customer, NACK to DLQ.
        Otherwise: requeue to original queue for another attempt.
        """
        if retry_count >= config.MAX_RETRIES - 1:
            logger.error(f"[{message.id}] Exhausted {config.MAX_RETRIES} retries — sending to DLQ")
            await self._repo.update_status(message.id, MessageStatus.FAILED)
            await self._notifier.notify(message, MessageStatus.FAILED)
            await raw.nack(requeue=False)
        else:
            logger.warning(
                f"[{message.id}] Send failed — requeuing "
                f"(attempt {retry_count + 1}/{config.MAX_RETRIES})"
            )
            await raw.nack(requeue=True)

    def _parse_message(self, raw: IncomingMessage):
        """Deserializes a raw RabbitMQ message body into a Message domain object."""
        data = json.loads(raw.body.decode())
        return Message(
            id=data["id"],
            content=data["content"],
            sender=Sender(
                name=data["sender_name"],
                email=data["sender_email"],
                phone=data["sender_phone"],
            ),
            destination=data["destination"],
            customer_type=CustomerType(data["customer_type"]),
            retry_count=data.get("retry_count", 0),
        )

    def _get_retry_count(self, raw: IncomingMessage):
        """
        Extracts the number of previous failed attempts from the x-death header.
        RabbitMQ increments this counter automatically on each NACK + requeue.
        """
        x_death = raw.headers.get("x-death", [])
        return x_death[0].get("count", 0) if x_death else 0
