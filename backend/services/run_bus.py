"""
In-process pub/sub for live run events.

A run is executed by a background task while the client subscribes over SSE.
Those two are decoupled by a per-run channel.

Each channel keeps a replay buffer of everything published so far, so a client
that connects a moment after the run starts still receives the earlier tokens
instead of joining mid-sentence.

This is deliberately in-memory and single-process. Running multiple workers
requires moving the channel to Redis; until then, run one worker (see
run_server.py) or clients may subscribe to a worker that is not executing their
run. Terminal state is always recoverable from the runs table regardless.
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)

# Bound the replay buffer so a very long run cannot grow without limit.
MAX_REPLAY_EVENTS = 2000


class RunChannel:
    """Fan-out channel for a single run."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._subscribers: List[asyncio.Queue] = []
        self._replay: List[Dict[str, Any]] = []
        self._closed = False

    def publish(self, event: Dict[str, Any]) -> None:
        """Broadcast an event to every subscriber and record it for replay."""
        if self._closed:
            return

        self._replay.append(event)
        if len(self._replay) > MAX_REPLAY_EVENTS:
            # Keep the head (run_started) so late joiners still get context.
            del self._replay[1:101]

        for queue in list(self._subscribers):
            queue.put_nowait(event)

    def close(self) -> None:
        """Signal end-of-stream to every subscriber."""
        self._closed = True
        for queue in list(self._subscribers):
            queue.put_nowait(None)

    @property
    def closed(self) -> bool:
        return self._closed

    async def subscribe(self) -> AsyncIterator[Dict[str, Any]]:
        """Yield replayed events, then live ones until the channel closes."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            for event in list(self._replay):
                yield event

            if self._closed:
                return

            while True:
                event = await queue.get()
                if event is None:
                    return
                yield event
        finally:
            if queue in self._subscribers:
                self._subscribers.remove(queue)


class RunBus:
    """Registry of active run channels."""

    def __init__(self):
        self._channels: Dict[str, RunChannel] = {}

    def open(self, run_id: str) -> RunChannel:
        """Create (or return) the channel for a run."""
        channel = self._channels.get(run_id)
        if channel is None:
            channel = RunChannel(run_id)
            self._channels[run_id] = channel
        return channel

    def get(self, run_id: str) -> Optional[RunChannel]:
        """Return an existing channel, or None if the run is not in flight."""
        return self._channels.get(run_id)

    def close(self, run_id: str) -> None:
        """Close a channel and drop it once subscribers have drained."""
        channel = self._channels.get(run_id)
        if channel:
            channel.close()

    def discard(self, run_id: str) -> None:
        """Remove a finished channel from memory."""
        self._channels.pop(run_id, None)


run_bus = RunBus()
