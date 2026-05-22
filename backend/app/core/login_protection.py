from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Optional

from redis import Redis

from app.core.config import settings


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_username(username: Optional[str]) -> str:
    return (username or "").strip().lower()


def _normalize_ip(ip_address: Optional[str]) -> str:
    return (ip_address or "unknown").strip()


def _redis_client() -> Optional[Redis]:
    if not settings.REDIS_URL:
        return None
    try:
        return Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None


@dataclass
class LoginProtectionResult:
    allowed: bool
    retry_after_seconds: int = 0


class LoginProtection:
    def __init__(self) -> None:
        self.redis = _redis_client()
        self.attempt_limit = settings.LOGIN_RATE_LIMIT_ATTEMPTS
        self.attempt_window_seconds = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
        self.lockout_seconds = settings.LOGIN_LOCKOUT_SECONDS
        self._memory: dict[str, dict[str, float | int]] = {}

    def _bucket_keys(self, ip_address: Optional[str], username: Optional[str]) -> list[tuple[str, str]]:
        normalized_ip = _normalize_ip(ip_address)
        normalized_username = _normalize_username(username)
        return [
            ("ip", _stable_hash(normalized_ip)),
            ("user", _stable_hash(normalized_username)) if normalized_username else ("user", _stable_hash("anonymous")),
        ]

    def _redis_keys(self, scope: str, digest: str) -> tuple[str, str]:
        return (f"cc:login:{scope}:{digest}:attempts", f"cc:login:{scope}:{digest}:lock")

    def check(self, ip_address: Optional[str], username: Optional[str]) -> LoginProtectionResult:
        if self.redis is not None:
            for scope, digest in self._bucket_keys(ip_address, username):
                attempts_key, lock_key = self._redis_keys(scope, digest)
                ttl = self.redis.ttl(lock_key)
                if ttl and ttl > 0:
                    return LoginProtectionResult(allowed=False, retry_after_seconds=int(ttl))

                attempts = self.redis.incr(attempts_key)
                if attempts == 1:
                    self.redis.expire(attempts_key, self.attempt_window_seconds)
                if attempts > self.attempt_limit:
                    self.redis.setex(lock_key, self.lockout_seconds, "1")
                    self.redis.delete(attempts_key)
                    return LoginProtectionResult(allowed=False, retry_after_seconds=self.lockout_seconds)
            return LoginProtectionResult(allowed=True)

        now = time.time()
        for scope, digest in self._bucket_keys(ip_address, username):
            entry = self._memory.get(f"{scope}:{digest}")
            if entry and entry.get("lock_until", 0) > now:
                return LoginProtectionResult(allowed=False, retry_after_seconds=int(entry["lock_until"] - now))

        for scope, digest in self._bucket_keys(ip_address, username):
            key = f"{scope}:{digest}"
            entry = self._memory.setdefault(key, {"attempts": 0, "window_expires_at": now + self.attempt_window_seconds, "lock_until": 0})
            if float(entry.get("window_expires_at", 0)) < now:
                entry["attempts"] = 0
                entry["window_expires_at"] = now + self.attempt_window_seconds
            entry["attempts"] = int(entry.get("attempts", 0)) + 1
            if int(entry["attempts"]) > self.attempt_limit:
                entry["lock_until"] = now + self.lockout_seconds
                entry["attempts"] = 0
                return LoginProtectionResult(allowed=False, retry_after_seconds=self.lockout_seconds)

        return LoginProtectionResult(allowed=True)

    def record_failure(self, ip_address: Optional[str], username: Optional[str]) -> None:
        if self.redis is not None:
            for scope, digest in self._bucket_keys(ip_address, username):
                attempts_key, lock_key = self._redis_keys(scope, digest)
                attempts = self.redis.incr(attempts_key)
                if attempts == 1:
                    self.redis.expire(attempts_key, self.attempt_window_seconds)
                if attempts >= self.attempt_limit:
                    self.redis.setex(lock_key, self.lockout_seconds, "1")
                    self.redis.delete(attempts_key)
            return

        now = time.time()
        for scope, digest in self._bucket_keys(ip_address, username):
            key = f"{scope}:{digest}"
            entry = self._memory.setdefault(key, {"attempts": 0, "window_expires_at": now + self.attempt_window_seconds, "lock_until": 0})
            if float(entry.get("window_expires_at", 0)) < now:
                entry["attempts"] = 0
                entry["window_expires_at"] = now + self.attempt_window_seconds
            entry["attempts"] = int(entry.get("attempts", 0)) + 1
            if int(entry["attempts"]) >= self.attempt_limit:
                entry["lock_until"] = now + self.lockout_seconds
                entry["attempts"] = 0

    def record_success(self, ip_address: Optional[str], username: Optional[str]) -> None:
        if self.redis is not None:
            for scope, digest in self._bucket_keys(ip_address, username):
                attempts_key, lock_key = self._redis_keys(scope, digest)
                self.redis.delete(attempts_key, lock_key)
            return

        for scope, digest in self._bucket_keys(ip_address, username):
            self._memory.pop(f"{scope}:{digest}", None)


login_protection = LoginProtection()