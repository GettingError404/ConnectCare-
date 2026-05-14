"""
Production-safe MQTT client manager.

Features:
- Optional MQTT enable/disable
- Auto reconnect with backoff
- Safe startup
- Redis buffering fallback
- Topic handlers
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable, Dict, Optional

import paho.mqtt.client as mqtt

try:
    import redis
except Exception:
    redis = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class MQTTClientManager:
    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._handlers: Dict[str, Callable[[str, bytes], None]] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._redis = None

        # Redis setup
        if redis and settings.REDIS_URL:
            try:
                self._redis = redis.from_url(settings.REDIS_URL)
                logger.info("✅ Redis connected for MQTT buffering")
            except Exception:
                logger.exception("❌ Failed to initialize Redis client")

    # ---------------------------------------------------
    # HANDLER REGISTRATION
    # ---------------------------------------------------

    def register_handler(self, topic: str, handler: Callable[[str, bytes], None]):
        self._handlers[topic] = handler
        logger.info(f"✅ MQTT handler registered: {topic}")
        try:
            from app.core import metrics
            metrics.inc_mqtt_message(result="handler_registered", tenant="-")
        except Exception:
            pass
    # ---------------------------------------------------
    # START / STOP
    # ---------------------------------------------------

    def start(self):

        # MQTT DISABLED
        if not getattr(settings, "ENABLE_MQTT", False):
            logger.warning("⚠️ MQTT is disabled")
            return

        # already running
        if self._thread and self._thread.is_alive():
            logger.info("MQTT thread already running")
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="mqtt-client-thread",
            daemon=True
        )

        self._thread.start()

        logger.info("✅ MQTT client manager started")

    def stop(self):
        self._stop_event.set()

        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                logger.exception("Error disconnecting MQTT")

        if self._thread:
            self._thread.join(timeout=2)

        logger.info("✅ MQTT client stopped")

    # ---------------------------------------------------
    # PUBLISH
    # ---------------------------------------------------

    def publish(
        self,
        topic: str,
        payload: dict,
        qos: int = 1,
        retain: bool = False
    ):

        message = json.dumps(payload)

        try:
            if not self._client:
                raise RuntimeError("MQTT client not connected")

            result = self._client.publish(
                topic,
                message,
                qos=qos,
                retain=retain
            )

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(f"Publish failed rc={result.rc}")

            logger.info(f"✅ MQTT published → {topic}")
            try:
                from app.core import metrics
                metrics.inc_mqtt_message(result="published", tenant="-")
            except Exception:
                pass

        except Exception:
            logger.exception("❌ MQTT publish failed")
            try:
                from app.core import metrics
                metrics.inc_mqtt_publish_failure(tenant="-")
            except Exception:
                pass

            # Redis fallback buffer
            if self._redis:
                try:
                    self._redis.rpush(
                        "mqtt_publish_buffer",
                        json.dumps({
                            "topic": topic,
                            "payload": payload
                        })
                    )

                    logger.info("✅ MQTT message buffered in Redis")

                except Exception:
                    logger.exception("❌ Failed buffering MQTT message")

    # ---------------------------------------------------
    # SUBSCRIBE
    # ---------------------------------------------------

    def subscribe(self, topic: str, qos: int = 1):

        if self._client:
            self._client.subscribe(topic, qos=qos)
            logger.info(f"✅ Subscribed to topic: {topic}")

    # ---------------------------------------------------
    # MAIN MQTT LOOP
    # ---------------------------------------------------

    def _run(self):

        backoff = 1

        while not self._stop_event.is_set():

            try:
                self._connect()

                # reset backoff after successful connect
                backoff = 1

                self._client.loop_forever()

            except Exception:

                logger.exception(
                    f"❌ MQTT disconnected. Reconnecting in {backoff}s"
                )

                time.sleep(backoff)

                backoff = min(backoff * 2, 60)

    # ---------------------------------------------------
    # CONNECT
    # ---------------------------------------------------

    def _connect(self):

        with self._lock:

            cfg = settings

            client_id = (
                cfg.MQTT_CLIENT_ID
                or "connectedcare-backend"
            )

            self._client = mqtt.Client(client_id=client_id)

            # username/password
            if cfg.MQTT_USERNAME and cfg.MQTT_PASSWORD:
                self._client.username_pw_set(
                    cfg.MQTT_USERNAME,
                    cfg.MQTT_PASSWORD
                )

            self._client.on_connect = self._on_connect
            self._client.on_message = self._on_message
            self._client.on_disconnect = self._on_disconnect

            logger.info(
                f"🔌 Connecting MQTT → "
                f"{cfg.MQTT_BROKER_HOST}:{cfg.MQTT_BROKER_PORT}"
            )

            self._client.connect(
                cfg.MQTT_BROKER_HOST,
                cfg.MQTT_BROKER_PORT,
                keepalive=60
            )

    # ---------------------------------------------------
    # CALLBACKS
    # ---------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc):

        if rc == 0:
            logger.info("✅ MQTT connected successfully")
        else:
            logger.error(f"❌ MQTT connection failed rc={rc}")

        # resubscribe
        for topic in self._handlers.keys():
            client.subscribe(topic)
            logger.info(f"✅ Re-subscribed → {topic}")

    def _on_disconnect(self, client, userdata, rc):

        logger.warning(f"⚠️ MQTT disconnected rc={rc}")

    def _on_message(self, client, userdata, msg):

        try:

            logger.info(f"📩 MQTT message received → {msg.topic}")
            try:
                from app.core import metrics
                metrics.inc_mqtt_message(result="received", tenant="-")
            except Exception:
                pass

            for topic_prefix, handler in self._handlers.items():

                if msg.topic.startswith(topic_prefix.rstrip("#")):

                    try:
                        handler(msg.topic, msg.payload)

                    except Exception:
                        logger.exception(
                            f"❌ MQTT handler error → {topic_prefix}"
                        )

        except Exception:
            logger.exception("❌ MQTT message processing error")


# ---------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------

mqtt_manager = MQTTClientManager()