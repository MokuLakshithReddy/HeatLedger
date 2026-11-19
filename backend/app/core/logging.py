import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict

SENSITIVE_KEYS = {"password", "token", "access_token", "secret", "authorization", "phone", "lat", "lon", "coordinates"}

def mask_sensitive_data(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: "***REDACTED***" if any(sk in k.lower() for sk in SENSITIVE_KEYS) else mask_sensitive_data(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    return data

class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "props"):
            log_record["context"] = mask_sensitive_data(record.props)
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logger(name: str = "heatledger") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
    return logger

logger = setup_logger()
