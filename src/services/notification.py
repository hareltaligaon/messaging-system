"""
notification.py - Customer notification service
Notifies the sender SMS and email on every outcome:
success, validation failure, or final send failure.
"""

import logging
from twilio.rest import Client as TwilioClient
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.models.message import Message, MessageStatus

logger = logging.getLogger(__name__)

_TEMPLATES = {
    MessageStatus.COMPLETED:
        "Your message to {destination} was delivered successfully.",
    MessageStatus.FAILED:
        "We were unable to deliver your message after multiple attempts. Please contact support.",
    MessageStatus.VALIDATION_FAILED:
        "Your message was rejected due to invalid details. Reason: {reason}",
}


class NotificationService:
    """
    Sends SMS and email notifications to the message sender.
    Notifies on every final outcome — success or failure.
    """

    def __init__(self, twilio_sid, twilio_token, twilio_from, sendgrid_key, sendgrid_from):
        self._twilio = TwilioClient(twilio_sid, twilio_token)
        self._twilio_from = twilio_from
        self._sendgrid = SendGridAPIClient(sendgrid_key)
        self._sendgrid_from = sendgrid_from

    async def notify(self, message: Message, status: MessageStatus, reason=""):
        """
        Sends SMS and email to the message sender with the outcome.
        Called on: Completed, ValidationFailed, and Failed (after max retries).
        """
        text = self._build_text(status, message, reason)
        subject = self._build_subject(status)

        self._send_sms(message.sender.phone, text)
        self._send_email(message.sender.email, subject, text)

        logger.info(f"[{message.id}] Notification sent to customer — status: {status}")

    def _build_text(self, status, message: Message, reason):
        """Renders the notification template for the given status."""
        template = _TEMPLATES.get(status, "Update on your message.")
        return template.format(destination=message.destination, reason=reason)

    def _build_subject(self, status):
        """Returns an email subject line for the given status."""
        return f"Message update — {status.value}"

    def _send_sms(self, phone, text):
        """Sends an SMS via Twilio. Logs errors without raising."""
        try:
            self._twilio.messages.create(body=text, from_=self._twilio_from, to=phone)
            logger.info(f"SMS sent to {phone}")
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {e}")

    def _send_email(self, to_email, subject, body):
        """Sends an email via SendGrid. Logs errors without raising."""
        try:
            mail = Mail(
                from_email=self._sendgrid_from,
                to_emails=to_email,
                subject=subject,
                plain_text_content=body,
            )
            self._sendgrid.send(mail)
            logger.info(f"Email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
