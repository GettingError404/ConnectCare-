from __future__ import annotations

import logging
from typing import Dict, Any

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


class NotificationProvider:
    def send(self, to: str, subject: str, body: str, metadata: Dict[str, Any] | None = None):
        raise NotImplementedError()


class EmailProvider(NotificationProvider):
    def send(self, to: str, subject: str, body: str, metadata: Dict[str, Any] | None = None):
        logger.info("Email send simulated to %s: %s", to, subject)


class SMSProvider(NotificationProvider):
    def send(self, to: str, subject: str, body: str, metadata: Dict[str, Any] | None = None):
        logger.info("SMS send simulated to %s: %s", to, body)


class PushProvider(NotificationProvider):
    def send(self, to: str, subject: str, body: str, metadata: Dict[str, Any] | None = None):
        logger.info("Push send simulated to %s: %s", to, body)


class WebSocketProvider(NotificationProvider):
    def send(self, to: str, subject: str, body: str, metadata: Dict[str, Any] | None = None):
        logger.info("WebSocket notification queued for tenant %s: %s", to, subject)


@celery_app.task()
def send_notification_task(provider: str, to: str, subject: str, body: str, metadata: Dict[str, Any] | None = None):
    try:
        if provider == "email":
            EmailProvider().send(to, subject, body, metadata)
        elif provider == "sms":
            SMSProvider().send(to, subject, body, metadata)
        elif provider == "push":
            PushProvider().send(to, subject, body, metadata)
        elif provider == "websocket":
            WebSocketProvider().send(to, subject, body, metadata)
        else:
            logger.warning("Unknown provider: %s", provider)
    except Exception:
        logger.exception("Failed to send notification")


class NotificationService:
    def __init__(self):
        pass

    def notify(self, channel: str, to: str, subject: str, body: str, metadata: Dict[str, Any] | None = None):
        # schedule async notification
        send_notification_task.delay(channel, to, subject, body, metadata)
