# src/banking_risk/logging.py
import logging
from logging.handlers import RotatingFileHandler
from banking_risk.config import LOGS_DIR

_LOG_FORMAT  = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_file_logging(log_file: str = "banking_risk.log") -> None:
    path    = LOGS_DIR / log_file
    handler = RotatingFileHandler(path, maxBytes=5_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    logging.getLogger("banking_risk").addHandler(handler)
    logging.getLogger("banking_risk").setLevel(logging.INFO)