import logging

from app.core.config import settings
from app.core.discord_handler import DiscordWebhookHandler


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if settings.LOGTAIL_SOURCE_TOKEN:
        from logtail import LogtailHandler

        logtail_handler = LogtailHandler(
            source_token=settings.LOGTAIL_SOURCE_TOKEN,
            host=settings.LOGTAIL_HOST,
        )
        logtail_handler.setFormatter(formatter)
        root.addHandler(logtail_handler)

    if settings.DISCORD_WEBHOOK_URL:
        discord_handler = DiscordWebhookHandler(settings.DISCORD_WEBHOOK_URL)
        discord_handler.setLevel(logging.ERROR)
        discord_handler.setFormatter(formatter)
        root.addHandler(discord_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
