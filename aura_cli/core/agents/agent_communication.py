"""Inter-agent communication system for Aura CLI.

CommunicationManager creates named channels and routes typed messages
(REQUEST, RESPONSE, NOTIFICATION, EVENT, DATA) between agents, with
support for broadcast and request/response patterns. Thread-safe.
"""

from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class MessageType(Enum):
    """Tipos de mensagem entre agentes."""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    EVENT = "event"
    DATA = "data"


@dataclass
class AgentMessage:
    """Inter-agent message dataclass (sender, receiver, content, type, timestamp)."""

    id: str
    sender_id: str
    receiver_id: Optional[str]
    message_type: MessageType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    response_to: Optional[str] = None


class CommunicationChannel:
    """
    Agent communication channel.

    Manages message sending and receiving between agents,
    supporting point-to-point communication and broadcast.to-a-ponto e broadcast.
    """

    # Memory management constants
    SENT_MESSAGES_MAX_SIZE = 1000
    SENT_MESSAGES_EVICT_COUNT = 200
    PENDING_RESPONSE_TTL = 300.0  # seconds

    def __init__(self, channel_id: str, name: str):
        """Initialise the communication manager."""
        self.channel_id = channel_id
        self.name = name

        self.message_queues: Dict[str, queue.Queue] = defaultdict(queue.Queue)
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self.pending_responses: Dict[str, queue.Queue] = {}
        self._pending_response_timestamps: Dict[str, float] = {}
        self.sent_messages: OrderedDict[str, AgentMessage] = OrderedDict()

        self.stats = get_stats()
        self.messages_sent = 0
        self.messages_received = 0

        self.lock = threading.Lock()

        logger.info(f"Communication channel '{name}' ({channel_id}) created")

    def register_agent(self, agent_id: str) -> None:
        """Register an agent on a channel."""
        with self.lock:
            if agent_id not in self.message_queues:
                self.message_queues[agent_id] = queue.Queue()
                logger.debug(f"Agent {agent_id} registrado no canal {self.channel_id}")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from a channel."""
        with self.lock:
            if agent_id in self.message_queues:
                del self.message_queues[agent_id]
                logger.debug(f"Agent {agent_id} removed from channel {self.channel_id}")

    def send_message(
        self,
        sender_id: str,
        receiver_id: Optional[str],
        message_type: MessageType,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
        requires_response: bool = False,
        response_to: Optional[str] = None,
    ) -> str:
        """Send a message to another agent and return the message ID."""
        import uuid

        message_id = str(uuid.uuid4())[:8]

        message = AgentMessage(
            id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            requires_response=requires_response,
            response_to=response_to,
        )

        with self.lock:
            # Evict oldest messages if sent_messages exceeds max size
            if len(self.sent_messages) >= self.SENT_MESSAGES_MAX_SIZE:
                for _ in range(
                    min(self.SENT_MESSAGES_EVICT_COUNT, len(self.sent_messages))
                ):
                    self.sent_messages.popitem(last=False)

            self.sent_messages[message_id] = message
            if response_to and response_to in self.pending_responses:
                self.pending_responses[response_to].put(message)

            if receiver_id:
                if receiver_id in self.message_queues:
                    self.message_queues[receiver_id].put(message)
                    self.messages_sent += 1

                    if requires_response:
                        self.pending_responses[message_id] = queue.Queue()
                        self._pending_response_timestamps[message_id] = time.time()

                    logger.debug(
                        f"Mensagem {message_id} enviada de {sender_id} para {receiver_id}"
                    )
                else:
                    logger.warning(
                        f"Agent destinatário {receiver_id} não está registrado no canal"
                    )
            else:
                sent_count = 0
                for agent_id, msg_queue in self.message_queues.items():
                    if agent_id != sender_id:
                        msg_queue.put(message)
                        sent_count += 1

                self.messages_sent += sent_count
                logger.debug(
                    f"Mensagem {message_id} enviada em broadcast de {sender_id} "
                    f"para {sent_count} agentes"
                )

        self.stats.track_tool_usage("agent_communication_send")

        return message_id

    def receive_message(
        self, agent_id: str, timeout: Optional[float] = None
    ) -> Optional[AgentMessage]:
        """Receive a message by ID, or None if not found."""
        if agent_id not in self.message_queues:
            logger.warning(f"Agent {agent_id} não está registrado no canal")
            return None

        try:
            message = self.message_queues[agent_id].get(timeout=timeout)
            self.messages_received += 1
            self.stats.track_tool_usage("agent_communication_receive")

            logger.debug(f"Agent {agent_id} recebeu mensagem {message.id}")

            handlers = self.message_handlers.get(message.message_type, [])
            for handler in handlers:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(
                        f"Error processing message handler {message.id}: {e}",
                        exc_info=True,
                    )

            return message

        except queue.Empty:
            return None

    def send_response(
        self,
        sender_id: str,
        original_message_id: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a reply to a received message and return the reply ID."""
        original_message = self.sent_messages.get(original_message_id)
        receiver_id = original_message.sender_id if original_message else None

        if receiver_id is None:
            logger.warning(
                f"Mensagem original {original_message_id} não encontrada; "
                "enviando resposta sem destinatário específico"
            )

        return self.send_message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=MessageType.RESPONSE,
            content=content,
            metadata=metadata or {},
            response_to=original_message_id,
        )

    def wait_for_response(
        self, message_id: str, timeout: Optional[float] = None
    ) -> Optional[AgentMessage]:
        """Wait for a reply with optional timeout. Returns message or None."""
        # Clean up stale pending responses older than TTL
        self._cleanup_stale_pending_responses()

        pending_queue = self.pending_responses.get(message_id)
        if not pending_queue:
            return None

        try:
            response = pending_queue.get(timeout=timeout)
            with self.lock:
                self.pending_responses.pop(message_id, None)
                self._pending_response_timestamps.pop(message_id, None)
            return response
        except queue.Empty:
            return None

    def _cleanup_stale_pending_responses(self) -> None:
        """Remove pending_responses entries older than PENDING_RESPONSE_TTL."""
        now = time.time()
        with self.lock:
            stale_ids = [
                msg_id
                for msg_id, ts in self._pending_response_timestamps.items()
                if now - ts > self.PENDING_RESPONSE_TTL
            ]
            for msg_id in stale_ids:
                self.pending_responses.pop(msg_id, None)
                self._pending_response_timestamps.pop(msg_id, None)
            if stale_ids:
                logger.debug(f"Cleaned up {len(stale_ids)} stale pending responses")

    def register_handler(
        self, message_type: MessageType, handler: Callable[[AgentMessage], None]
    ) -> None:
        """Register a handler function for a message type."""
        self.message_handlers[message_type].append(handler)
        logger.debug(f"Handler registrado para tipo {message_type.value}")

    def get_statistics(self) -> Dict[str, Any]:
        """Return communication statistics as a dict."""
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "registered_agents": len(self.message_queues),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "pending_responses": len(self.pending_responses),
            "tracked_messages": len(self.sent_messages),
        }

    def __repr__(self) -> str:
        """Return a string representation of the channel."""
        return (
            f"<CommunicationChannel(id={self.channel_id}, "
            f"agents={len(self.message_queues)})>"
        )


class CommunicationManager:
    """Manages communication channels between agents."""

    def __init__(self):
        """Initialise the communication manager."""
        self.channels: Dict[str, CommunicationChannel] = {}
        self.default_channel: Optional[CommunicationChannel] = None

        logger.info("CommunicationManager initialized")

    def create_channel(self, channel_id: str, name: str) -> CommunicationChannel:
        """Create a new communication channel."""
        channel = CommunicationChannel(channel_id, name)
        self.channels[channel_id] = channel

        if not self.default_channel:
            self.default_channel = channel

        logger.info(f"Channel '{name}' ({channel_id}) created")
        return channel

    def get_channel(
        self, channel_id: Optional[str] = None
    ) -> Optional[CommunicationChannel]:
        """Get or create a communication channel by ID."""
        if channel_id:
            return self.channels.get(channel_id)
        return self.default_channel

    def register_agent(self, agent_id: str, channel_id: Optional[str] = None) -> None:
        """Register an agent on a channel."""
        channel = self.get_channel(channel_id)
        if channel:
            channel.register_agent(agent_id)
        else:
            logger.warning(
                f"Channel {channel_id} not found to register agent {agent_id}"
            )

    def send_message(
        self,
        sender_id: str,
        receiver_id: Optional[str],
        message_type: MessageType,
        content: Any,
        channel_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Send a message to another agent and return the message ID."""
        channel = self.get_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

        return channel.send_message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            content=content,
            **kwargs,
        )

    def receive_message(
        self,
        agent_id: str,
        channel_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[AgentMessage]:
        """Receive a message by ID, or None if not found."""
        channel = self.get_channel(channel_id)
        if not channel:
            return None

        return channel.receive_message(agent_id, timeout)

    def wait_for_response(
        self,
        message_id: str,
        channel_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Optional[AgentMessage]:
        """Wait for a reply with optional timeout. Returns message or None."""
        channel = self.get_channel(channel_id)
        if not channel:
            return None

        return channel.wait_for_response(message_id, timeout)

    def get_statistics(self) -> Dict[str, Any]:
        """Return communication statistics as a dict."""
        return {
            "channels_count": len(self.channels),
            "channels": {
                ch_id: ch.get_statistics() for ch_id, ch in self.channels.items()
            },
        }

    def __repr__(self) -> str:
        """Return a string representation of the manager."""
        return f"<CommunicationManager(channels={len(self.channels)})>"
