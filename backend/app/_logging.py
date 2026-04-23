import logging
import os


def _resolve_log_level() -> int:
    raw = (os.getenv("NLIP_LOG_LEVEL") or "INFO").strip().upper()
    return getattr(logging, raw, logging.INFO)


def _configure_nlip_logger() -> logging.Logger:
    logger = logging.getLogger("NLIP")
    logger.setLevel(_resolve_log_level())

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.propagate = False
    return logger


logger = _configure_nlip_logger()

def log_to_console(level):
    logger.setLevel(level)
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                                      datefmt='%H:%M:%S')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)