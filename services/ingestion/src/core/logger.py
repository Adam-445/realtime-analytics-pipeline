import logging


def get_logger(name: str) -> logging.Logger:
    """Get preconfigured structured logger"""
    logger = logging.getLogger(name)
    logger.propagate = True
    return logger
