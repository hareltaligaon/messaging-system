"""
message.py - Message domain model
Defines the core data structures used throughout the system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MessageStatus(str, Enum):
    """Lifecycle statuses of a message as it moves through the system."""
    RECEIVED = "Received"
    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    VALIDATION_FAILED = "ValidationFailed"
    FAILED = "Failed"


class CustomerType(str, Enum):
    """Customer tier — VIP messages always take priority over regular ones."""
    VIP = "vip"
    REGULAR = "regular"


@dataclass
class Sender:
    """Encapsulates all sender-related fields."""
    name: str
    email: str
    phone: str


@dataclass
class Message:
    """
    Represents a single message flowing through the system.

    Attributes:
        id - unique message identifier
        content - the message body to be delivered
        sender - sender details (name, email, phone)
        destination - target address for delivery
        customer_type - VIP or regular (determines queue priority)
        status - current lifecycle status
        retry_count - number of failed send attempts so far
        created_at - UTC timestamp of message creation
    """
    id: str
    content: str
    sender: Sender
    destination: str
    customer_type: CustomerType
    status: MessageStatus = MessageStatus.RECEIVED
    retry_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_vip(self):
        """Returns True if the message belongs to a VIP customer."""
        return self.customer_type == CustomerType.VIP

    def queue_name(self, vip_queue, regular_queue):
        """Returns the appropriate RabbitMQ queue name based on customer type."""
        return vip_queue if self.is_vip() else regular_queue
