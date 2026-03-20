"""Logger padronizado Piranha Supplies."""

import logging
import sys


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Configura logger com formato padronizado.
    Args:
        name: nome do logger (normalmente __name__)
        level: nível de log ("DEBUG", "INFO", "WARNING", "ERROR")
    Returns:
        instância configurada do Logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
