import json
import logging
from typing import Any

from pydantic import BaseModel


LOGGER_NAME = "failure_forensics.pipeline"


def configure_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    return value


def log_step(
    *,
    logger: logging.Logger,
    step_name: str,
    step_input: Any,
    step_output: Any | None = None,
    success: bool,
    error: str | None = None,
) -> None:
    payload = {
        "step_name": step_name,
        "input": _serialize(step_input),
        "output": _serialize(step_output) if step_output is not None else None,
        "success": success,
        "error": error,
    }
    logger.info(json.dumps(payload, ensure_ascii=True))

