"""
Logging utilities for the premium batch job.

This module exposes the project logger used across the pipeline to
provide consistent runtime visibility for ingestion, validation,
transformation, and output generation.
"""

import logging
from typing import Literal, Union

LogLevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _to_numeric(log_level: Union[int, LogLevelName]) -> int:
    """
    Convert log level to numeric if not already given as
    in the numeric form.
    >>> _to_numeric(log_level=20)
    20
    >>> _to_numeric(log_level="DEBUG")
    10
    """
    return (
        log_level
        if isinstance(log_level, int)
        else getattr(logging, log_level, logging.INFO)
    )


def get_configured_logger(
    log_level: Union[int, LogLevelName] = "INFO",
) -> logging.Logger:
    """
    Uses Cloud Logging if the code runs in
    Cloud Run/Functions (Gen 2) but uses basicConfig
    i.e. the console if run locally.
    If running on the Cloud, the K_SERVICE variable is set.
    Returns a module logger to use throughout the app.
    """
    numeric_level = _to_numeric(log_level)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(numeric_level)
    return logger
