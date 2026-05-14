"""
Event Bus - Lightweight pub/sub system for pipeline events
"""

import asyncio
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)


class EventBus:
    """Simple synchronous event bus for pipeline stage communication"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)

    def on(self, event: str, callback: Callable):
        """Register a listener for an event"""
        self._listeners[event].append(callback)

    def off(self, event: str, callback: Callable):
        """Remove a listener"""
        if event in self._listeners:
            self._listeners[event].remove(callback)

    def emit(self, event: str, data: Any = None):
        """Emit an event to all listeners"""
        for callback in self._listeners.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"EventBus listener error for '{event}': {e}")

    async def emit_async(self, event: str, data: Any = None):
        """Emit an event, calling async listeners with await"""
        for callback in self._listeners.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"EventBus async listener error for '{event}': {e}")
