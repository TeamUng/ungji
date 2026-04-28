import logging
import threading
import time

import httpx


class DiscordWebhookHandler(logging.Handler):
    def __init__(self, webhook_url: str, rate_limit_seconds: int = 60):
        super().__init__()
        self.webhook_url = webhook_url
        self.rate_limit_seconds = rate_limit_seconds
        self._lock = threading.Lock()
        self._last_emitted: dict[str, float] = {}

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if not self.webhook_url:
                return

            message = self.format(record)
            dedup_key = f"{record.name}:{record.lineno}:{message[:50]}"

            now = time.monotonic()
            with self._lock:
                last = self._last_emitted.get(dedup_key, 0.0)
                if now - last < self.rate_limit_seconds:
                    return
                self._last_emitted[dedup_key] = now

            if len(message) > 1900:
                message = message[:1900]

            httpx.post(
                self.webhook_url,
                json={"content": f"```\n{message}\n```"},
                timeout=5.0,
            )
        except Exception:
            pass
