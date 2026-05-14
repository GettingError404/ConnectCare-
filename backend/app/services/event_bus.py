import json
import logging
from typing import Dict, Any

try:
    import redis
except Exception:
    redis = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._client = None
        if redis and settings.REDIS_URL:
            try:
                self._client = redis.from_url(settings.REDIS_URL)
            except Exception:
                logger.exception("Failed to connect to Redis for EventBus")

    def publish(self, channel: str, event: Dict[str, Any]):
        payload = json.dumps(event, default=str)
        try:
            if self._client:
                try:
                    self._client.publish(channel, payload)
                    try:
                        from app.core import metrics
                        metrics.inc_eventbus_publish(channel=channel, status="ok")
                    except Exception:
                        pass
                except Exception:
                    logger.exception("Failed to publish event to Redis: %s", channel)
                    try:
                        from app.core import metrics
                        metrics.inc_eventbus_publish(channel=channel, status="failed")
                    except Exception:
                        pass
            else:
                logger.info("EventBus publish (no Redis): %s %s", channel, payload)
                try:
                    from app.core import metrics
                    metrics.inc_eventbus_publish(channel=channel, status="no_redis")
                except Exception:
                    pass
        except Exception:
            logger.exception("Unexpected error in EventBus.publish")


event_bus = EventBus()
