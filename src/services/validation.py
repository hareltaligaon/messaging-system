"""
validation.py - Message validation service
Validates all required fields of a message before it is sent.
"""

import re
import logging
from src.models.message import Message

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Validates incoming messages before processing.
    All validation rules are encapsulated as private methods
    and composed in the main validate() entry point.
    """

    _EMAIL_PATTERN = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$')
    _PHONE_PATTERN = re.compile(r'^[\d\s\-\+]{7,15}$')

    def validate(self, message: Message):
        """
        Runs all validation checks on the message.
        Returns on the first failure found.

        Returns:
            (True, "") - message is valid
            (False, reason) - message is invalid, with the failure reason
        """
        checks = [
            self._validate_content,
            self._validate_sender_name,
            self._validate_email,
            self._validate_phone,
            self._validate_destination,
        ]
        for check in checks:
            valid, reason = check(message)
            if not valid:
                logger.warning(f"[{message.id}] Validation failed: {reason}")
                return False, reason

        logger.info(f"[{message.id}] Validation passed")
        return True, ""

    def _validate_content(self, message: Message):
        """Ensures the message body is not empty."""
        if not message.content or not message.content.strip():
            return False, "Message content is empty"
        return True, ""

    def _validate_sender_name(self, message: Message):
        """Ensures the sender name is present."""
        if not message.sender.name or not message.sender.name.strip():
            return False, "Sender name is missing"
        return True, ""

    def _validate_email(self, message: Message):
        """Validates the sender email format."""
        if not message.sender.email:
            return False, "Sender email is missing"
        if not self._EMAIL_PATTERN.match(message.sender.email):
            return False, f"Invalid email format: {message.sender.email}"
        return True, ""

    def _validate_phone(self, message: Message):
        """Validates the sender phone number format."""
        if not message.sender.phone:
            return False, "Sender phone is missing"
        if not self._PHONE_PATTERN.match(message.sender.phone):
            return False, f"Invalid phone format: {message.sender.phone}"
        return True, ""

    def _validate_destination(self, message: Message):
        """Ensures the destination address is present."""
        if not message.destination or not message.destination.strip():
            return False, "Destination address is missing"
        return True, ""
