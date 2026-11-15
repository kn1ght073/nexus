"""In-process event bus (architecture plan §2.1).

Domain events (TASK_CREATED, PROJECT_UPDATED, ...) are published here after
commit; subscribers are the WebSocket broadcaster, the activity logger and,
later, the automation engine. An asyncio.Queue bridges the synchronous
SQLAlchemy handlers to the async WebSocket loop without extra threads.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

_subscribers: list[asyncio.Queue] = []


@dataclass
class DomainEvent:
    type: str
    user_id: int
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "user_id": self.user_id,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
        }


def subscribe() -> asyncio.Queue:
    """Register a new event subscriber (the WebSocket manager calls this)."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _subscribers.append(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    if queue in _subscribers:
        _subscribers.remove(queue)


def publish(event: DomainEvent) -> None:
    """Fan out to all subscribers; slow consumers drop events instead of blocking."""
    payload = event.to_dict()
    for queue in list(_subscribers):
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # drop: live push is best-effort; clients fall back to pull


async def publish_async(event: DomainEvent) -> None:
    publish(event)
