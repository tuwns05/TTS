"""Privacy-conscious Loguru configuration."""

from __future__ import annotations

import sys

from loguru import logger

from vntts.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure console and rotating file logs without recording user payloads."""

    logger.remove()
    if settings.application.environment.lower() == "development":
        logger.add(
            sys.stderr,
            level=settings.logging.level,
            colorize=True,
            backtrace=False,
            diagnose=False,
        )
    logger.add(
        settings.paths.logs_dir / "vntts.log",
        level=settings.logging.level,
        rotation="10 MB",
        retention=f"{settings.logging.retention_days} days",
        encoding="utf-8",
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )


def shutdown_logging() -> None:
    """Flush queued log messages before application shutdown."""

    logger.complete()
