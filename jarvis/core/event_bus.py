"""Lightweight decoupled EventBus for JARVIS."""

import asyncio
import inspect
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List, Union
import logging
from jarvis.core.state import JarvisEvent, EventType

logger = logging.getLogger("jarvis.core.event_bus")

EventHandler = Union[Callable[[JarvisEvent], None], Callable[[JarvisEvent], Coroutine[Any, Any, None]]]


class EventBus:
    """Thread-safe and async-compatible publish/subscribe event bus."""

    def __init__(self):
        self._subscribers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._all_subscribers: List[EventHandler] = []

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._all_subscribers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: JarvisEvent) -> None:
        """Publish an event to all registered synchronous and asynchronous listeners."""
        handlers = list(self._subscribers.get(event.event_type, [])) + list(self._all_subscribers)
        for h in handlers:
            try:
                if inspect.iscoroutinefunction(h):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(h(event))
                    except RuntimeError:
                        asyncio.run(h(event))
                else:
                    h(event)
            except Exception as e:
                logger.error(f"Error handling event {event.event_type}: {e}", exc_info=True)


# Global event bus
bus = EventBus()
