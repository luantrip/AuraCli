"""Optional streaming helpers for real-time lateral data flows.

StreamManager maintains a registry of named streams (TEXT, JSON, BINARY,
LOG, METRIC), each with a configurable buffer and subscriber callbacks.
Optional support infrastructure — not the main agent runtime coordination path.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class StreamType(Enum):
    """Stream types."""

    TEXT = "text"
    JSON = "json"
    BINARY = "binary"
    LOG = "log"
    METRIC = "metric"


@dataclass
class Stream:
    """Data stream (stream_id, stream_type, buffer)."""

    stream_id: str
    stream_type: StreamType
    buffer: deque = field(default_factory=deque)
    max_size: int = 1000
    subscribers: List[Callable] = field(default_factory=list)


class StreamManager:
    """Stream manager with pub/sub and buffer management."""

    def __init__(self):
        """Initialise the stream manager."""
        self.streams: Dict[str, Stream] = {}
        self.stats = get_stats()

        logger.info("StreamManager initialized")

    def create_stream(
        self,
        stream_id: str,
        stream_type: StreamType = StreamType.TEXT,
        max_size: int = 1000,
    ) -> Stream:
        """Create a new stream."""
        stream = Stream(stream_id=stream_id, stream_type=stream_type, max_size=max_size)

        self.streams[stream_id] = stream

        logger.debug(f"Stream '{stream_id}' created")

        return stream

    def publish(self, stream_id: str, data: Any) -> None:
        """
        Publica dados em um stream.

        Args:
            stream_id: ID do stream
            data: Dados a publicar
        """
        if stream_id not in self.streams:
            logger.warning(f"Stream '{stream_id}' not found")
            return

        stream = self.streams[stream_id]

        stream.buffer.append(data)

        while len(stream.buffer) > stream.max_size:
            stream.buffer.popleft()

        for subscriber in stream.subscribers:
            try:
                subscriber(data)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}", exc_info=True)

        logger.debug(f"Dados publicados em '{stream_id}'")

    def subscribe(self, stream_id: str, callback: Callable[[Any], None]) -> None:
        """Subscribe to a stream."""
        if stream_id not in self.streams:
            logger.warning(f"Stream '{stream_id}' not found")
            return

        self.streams[stream_id].subscribers.append(callback)

        logger.debug(f"Assinatura adicionada ao stream '{stream_id}'")

    async def stream_async(self, stream_id: str) -> AsyncIterator[Any]:
        """Return an async iterator for a stream."""
        if stream_id not in self.streams:
            return

        stream = self.streams[stream_id]
        queue: asyncio.Queue[Any] = asyncio.Queue()

        def enqueue(data):
            """Enqueue data for streaming."""
            queue.put_nowait(data)

        stream.subscribers.append(enqueue)

        try:
            while True:
                data = await queue.get()
                yield data
        finally:
            if enqueue in stream.subscribers:
                stream.subscribers.remove(enqueue)

    def get_stream_data(self, stream_id: str, limit: int = 100) -> List[Any]:
        """Get data from a stream."""
        if stream_id not in self.streams:
            return []

        stream = self.streams[stream_id]

        return list(stream.buffer)[-limit:]

    def delete_stream(self, stream_id: str) -> bool:
        """Delete a stream by ID."""
        if stream_id in self.streams:
            del self.streams[stream_id]
            logger.debug(f"Stream '{stream_id}' removed")
            return True

        return False
