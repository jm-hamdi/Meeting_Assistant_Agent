"""Centralised logging setup with colorised output."""

from __future__ import annotations

import logging

from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)

_LEVEL_COLORS = {
    logging.DEBUG: Fore.CYAN,
    logging.INFO: Fore.GREEN,
    logging.WARNING: Fore.YELLOW,
    logging.ERROR: Fore.RED,
    logging.CRITICAL: Fore.MAGENTA,
}


class _ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname:<8}{Style.RESET_ALL}"
        return super().format(record)


def setup_logging(verbosity: int = 1) -> None:
    """Configure root logger.

    verbosity: 0 = WARNING, 1 = INFO, 2 = DEBUG
    """
    level_map = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}
    level = level_map.get(verbosity, logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(
        _ColorFormatter(
            fmt="%(levelname)s %(name)s — %(message)s",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "litellm", "openai", "faster_whisper"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
