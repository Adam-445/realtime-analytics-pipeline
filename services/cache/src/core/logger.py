import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.propagate = True
    return logger
