import logging, sys

def get_logger(name="pantrypilot"):
    logger = logging.getLogger(name)
    if logger.handlers:  # avoid dupes
        return logger
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger