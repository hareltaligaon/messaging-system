"""
sending.py - External message sending service
Responsible for delivering the message to the external sending API.
"""

import logging
import httpx
from src.models.message import Message

logger = logging.getLogger(__name__)


class SendingService:
    """
    Sends messages to an external delivery API via HTTP POST.
    Handles timeouts and network errors gracefully.
    """

    def __init__(self, service_url, timeout=10.0):
        self._service_url = service_url
        self._timeout = timeout

    async def send(self, message: Message):
        """
        Delivers the message to the external sending service.

        Returns:
            True - delivery was acknowledged (HTTP 2xx)
            False - delivery failed (network error, timeout, or non-2xx response)
        """
        payload = self._build_payload(message)
        try:
            return await self._post(payload, message.id)
        except httpx.TimeoutException:
            logger.error(f"[{message.id}] Sending service timed out")
            return False
        except httpx.RequestError as e:
            logger.error(f"[{message.id}] Network error while sending: {e}")
            return False

    def _build_payload(self, message: Message):
        """Constructs the JSON payload for the external sending service."""
        return {
            "message_id": message.id,
            "content": message.content,
            "destination": message.destination,
            "sender_name": message.sender.name,
            "customer_type": message.customer_type,
        }

    async def _post(self, payload, message_id):
        """Executes the HTTP POST and evaluates the response."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._service_url, json=payload)

        if response.is_success:
            logger.info(f"[{message_id}] Successfully delivered to external service")
            return True

        logger.warning(f"[{message_id}] External service returned {response.status_code}")
        return False
