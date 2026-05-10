#!/usr/bin/env python3
"""llmemos_logger — optional custom logger for llmemos tools.

Drop-in replacement for stdlib logging.getLogger() with colored output
and two additional log levels: NOTICE (25) and SUCCESS (35).

Colored output requires the coloredlogs package (pip install coloredlogs).
Falls back to plain stdlib logging if coloredlogs is not installed.

Usage:
    from llmemos_logger import get_logger
    import logging
    logger = get_logger(__name__, level=logging.DEBUG)
    logger.notice("Something noteworthy")
    logger.success("Task complete")

If this file is not importable, llmemos tools fall back to stdlib logging
silently — no action required from the user.

To use your own logging implementation, replace this file with any module
that exports get_logger(name, level) -> logging.Logger.
"""

import logging

try:
    import coloredlogs
except ImportError:
    coloredlogs = None

NOTICE = 25
SUCCESS = 35

logging.addLevelName(NOTICE, "NOTICE")
logging.addLevelName(SUCCESS, "SUCCESS")


def _logger_notice(self, msg: str, *args, **kwargs) -> None:
    self.log(NOTICE, msg, *args, **kwargs)


def _logger_success(self, msg: str, *args, **kwargs) -> None:
    self.log(SUCCESS, msg, *args, **kwargs)


if not hasattr(logging.Logger, "notice"):
    logging.Logger.notice = _logger_notice  # type: ignore[attr-defined]
if not hasattr(logging.Logger, "success"):
    logging.Logger.success = _logger_success  # type: ignore[attr-defined]


def _attach_logger_aliases(lgr: logging.Logger) -> None:
    """Attach notice/success convenience methods to a logger instance."""

    def notice(msg: str, *args, **kwargs) -> None:
        lgr.log(NOTICE, msg, *args, **kwargs)

    def success(msg: str, *args, **kwargs) -> None:
        lgr.log(SUCCESS, msg, *args, **kwargs)

    lgr.notice = notice  # type: ignore[attr-defined]
    lgr.success = success  # type: ignore[attr-defined]


def get_logger(name: str | None = None, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger with custom levels and optional colored output.

    Args:
        name:  Logger name. Pass __name__ from the calling module.
        level: Initial logging level (default: logging.INFO).

    Returns:
        logging.Logger with notice() and success() methods attached.
    """
    logger = logging.getLogger(name)
    fmt = "%(asctime)s - %(levelname)s - %(lineno)d - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    if coloredlogs:
        formatter = coloredlogs.ColoredFormatter(fmt=fmt, datefmt=datefmt)
    else:
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if coloredlogs:
        coloredlogs.install(level=level, logger=logger)
    else:
        logger.setLevel(level)

    _attach_logger_aliases(logger)
    return logger
