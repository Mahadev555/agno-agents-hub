"""
Single place where logging is configured.

Previously five modules each called logging.basicConfig(); only the first import
won, so log level and format depended on import order. Configure once, here,
from app startup.
"""

import logging
import os
import sys

# Runs are traced by threading the run id through as the session id, so it
# appears in messages as "[<run_id>] ...". Keeping the format stable makes those
# greppable until structured JSON logging is worth the dependency.
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"
DATE_FORMAT = "%H:%M:%S"


def configure_logging() -> None:
    """Install a single stdout handler on the root logger."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    root = logging.getLogger()
    # Replace anything a stray basicConfig() already installed.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)

    # These are chatty at INFO and drown out anything useful.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("primp").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
