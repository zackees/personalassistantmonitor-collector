"""
Logging module for personalmonitor_collector.
"""

import os
from logging import getLogger, INFO, Logger, Formatter, StreamHandler
from concurrent_log_handler import ConcurrentRotatingFileHandler  # type: ignore
from personalmonitor_collector.settings import (
    LOG_DIR,
    LOG_SIZE,
    LOG_HISTORY,
    LOGGING_FMT,
    LOGGING_USE_GZIP,
)


def make_logger(name: str) -> Logger:
    """TODO - Add description."""
    log = getLogger(name)
    # Use an absolute path to prevent file rotation trouble.
    logfile = os.path.join(LOG_DIR, "system.log")
    # Rotate log after reaching LOG_SIZE, keep LOG_HISTORY old copies.
    rotate_handler = ConcurrentRotatingFileHandler(
        logfile, "a", LOG_SIZE, LOG_HISTORY, use_gzip=LOGGING_USE_GZIP, encoding="utf-8"
    )
    rotate_handler.setFormatter(Formatter(LOGGING_FMT))
    log.addHandler(rotate_handler)
    log.setLevel(INFO)
    formatter = Formatter(LOGGING_FMT)
    strmhandler = StreamHandler()
    strmhandler.setFormatter(formatter)
    log.addHandler(strmhandler)
    return log


def main() -> None:
    """TODO - Add description."""
    logger = make_logger(__name__)
    logger.info("Hello world")


if __name__ == "__main__":
    main()
