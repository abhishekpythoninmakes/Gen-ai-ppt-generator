"""
Production-grade SSE event bus for streaming slide generation events.

Designed for concurrent multi-user use:
  - Each generation job gets its own event queue
  - Supports multiple subscribers (reconnecting clients)
  - Stores event history so reconnecting clients can catch up
  - Auto-cleans resources after stream ends
  - Fully async, zero blocking
"""

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator

logger = logging.getLogger(__name__)

# How long to keep completed streams in memory for late joins / reconnects (seconds)
_STREAM_TTL = 120


class _JobStream:
    """Internal per-job stream state."""

    __slots__ = ("job_id", "events", "subscribers", "closed", "created_at", "closed_at")

    def __init__(self, job_id: int):
        self.job_id = job_id
        self.events: list[dict] = []  # ordered history of all pushed events
        self.subscribers: list[asyncio.Queue] = []
        self.closed = False
        self.created_at = time.monotonic()
        self.closed_at: float | None = None


class StreamManager:
    """
    Singleton event bus for SSE generation streams.

    Usage (producer side – inside generation coroutine):
        stream_mgr.create_stream(job_id)
        stream_mgr.push_event(job_id, "theme", {...})
        stream_mgr.push_event(job_id, "slide", {...})
        stream_mgr.push_event(job_id, "complete", {...})
        stream_mgr.close_stream(job_id)

    Usage (consumer side – SSE endpoint):
        async for event_type, data in stream_mgr.subscribe(job_id):
            yield f"event: {event_type}\\ndata: {json.dumps(data)}\\n\\n"
    """

    def __init__(self):
        self._streams: dict[int, _JobStream] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    # ── Lifecycle ────────────────────────────────────────

    def create_stream(self, job_id: int) -> None:
        """Create a new event stream for a generation job."""
        stream = _JobStream(job_id)
        self._streams[job_id] = stream
        logger.debug(f"Stream created for job {job_id}")
        self._ensure_cleanup()

    def push_event(self, job_id: int, event_type: str, data: Any) -> None:
        """Push an event to all subscribers of this job's stream."""
        stream = self._streams.get(job_id)
        if not stream:
            logger.warning(f"push_event: no stream for job {job_id}")
            return
        if stream.closed:
            logger.warning(f"push_event: stream already closed for job {job_id}")
            return

        event = {"event": event_type, "data": data}
        stream.events.append(event)

        # Fan-out to all subscriber queues (non-blocking)
        dead = []
        for i, q in enumerate(stream.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(i)
        # Remove dead subscribers
        for i in reversed(dead):
            stream.subscribers.pop(i)

        logger.debug(
            f"Job {job_id}: pushed '{event_type}' → {len(stream.subscribers)} subscriber(s)"
        )

    def close_stream(self, job_id: int) -> None:
        """Mark a stream as closed; subscribers will get a sentinel and exit."""
        stream = self._streams.get(job_id)
        if not stream:
            return
        stream.closed = True
        stream.closed_at = time.monotonic()
        # Send sentinel (None) to all subscribers so their async-for exits
        for q in stream.subscribers:
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass
        logger.debug(f"Stream closed for job {job_id}")

    async def subscribe(
        self, job_id: int, last_event_index: int = 0
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """
        Async generator that yields (event_type, data) tuples.

        Replays any events from `last_event_index` onwards (for reconnection),
        then waits for live events.
        """
        stream = self._streams.get(job_id)
        if not stream:
            logger.warning(f"subscribe: no stream for job {job_id}")
            return

        # Create subscriber queue
        q: asyncio.Queue = asyncio.Queue(maxsize=256)
        stream.subscribers.append(q)

        try:
            # Replay historical events the client hasn't seen
            for event in stream.events[last_event_index:]:
                yield event["event"], event["data"]

            # If stream is already closed, no need to wait
            if stream.closed:
                return

            # Listen for live events
            while True:
                event = await q.get()
                if event is None:
                    # Sentinel — stream closed
                    return
                yield event["event"], event["data"]

        finally:
            # Remove ourselves from subscribers
            try:
                stream.subscribers.remove(q)
            except ValueError:
                pass

    def has_stream(self, job_id: int) -> bool:
        """Check if a stream exists (active or recently closed)."""
        return job_id in self._streams

    def stream_event_count(self, job_id: int) -> int:
        """How many events have been emitted for this job."""
        stream = self._streams.get(job_id)
        return len(stream.events) if stream else 0

    # ── Cleanup ──────────────────────────────────────────

    def _ensure_cleanup(self) -> None:
        """Ensure background cleanup coroutine is running."""
        if self._cleanup_task and not self._cleanup_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
            self._cleanup_task = loop.create_task(self._cleanup_loop())
        except RuntimeError:
            pass

    async def _cleanup_loop(self) -> None:
        """Periodically evict closed streams that have exceeded TTL."""
        while True:
            await asyncio.sleep(30)
            now = time.monotonic()
            expired = [
                jid
                for jid, s in self._streams.items()
                if s.closed and s.closed_at and (now - s.closed_at) > _STREAM_TTL
            ]
            for jid in expired:
                del self._streams[jid]
                logger.debug(f"Cleaned up expired stream for job {jid}")
            # Stop loop if no streams left
            if not self._streams:
                break


# ── Module-level singleton ───────────────────────────────
stream_manager = StreamManager()
