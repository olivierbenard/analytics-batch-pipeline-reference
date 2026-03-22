"""
Input reading utilities for the premium batch job.

This module is responsible for loading raw transaction records from JSON
files and validating their top-level structural shape before business
validation begins.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from batch_pipeline_reference import logger
from batch_pipeline_reference.config import (
    ENCODING,
)


def _check_payload(payload: Any) -> None:
    """
    Validate the structure of the loaded JSON payload.
    Ensures that the top-level structure is a list of dictionaries,
    where each dictionaries represents a transaction record.

    Raises
    -----
    ValueError
        If the payload structure does not match the expected format.
    """
    if not isinstance(payload, list):
        raise ValueError("Expected input JSON to be a list of transaction records.")
    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            raise ValueError(f"Expected record at index {index} to be a dict object.")


def read_transactions(input_path: Path) -> list[dict[str, Any]]:
    """
    Read raw transaction records from a JSON file.

    The input file is expected to contain a JSON array where each
    element is a transaction object.

    This function only loads and validates the raw structure of the
    data. It intentionally does not perform business validation or
    type normalization. These steps are handled later in the
    transformation layer.

    Parameters
    ----------
    input_path : Path
        Path to the input JSON file containing transaction records.

    Returns
    -------
    list[dict[str, Any]]
        A list of raw transaction dictionaries as read from the file.

    Raises
    ------
    ValueError
        If the JSON structure is not a list of objects.
    """
    logger.info("Reading transaction file: %s", input_path)

    with input_path.open("r", encoding=ENCODING) as file:
        payload = json.load(file)

    _check_payload(payload)

    logger.info("Loaded %d transaction records", len(payload))
    return payload
