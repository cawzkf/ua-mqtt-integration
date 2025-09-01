import logging, sys

def setup_logging(level: str ="INFO")-> logging.Logger:
    logging.basicConfig(
        level = getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s]: %(message)s",
        stream=sys.stdout,
    )
    return logging.getLogger("logger")