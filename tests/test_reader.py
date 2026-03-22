from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from batch_pipeline_reference.config import ENCODING
from batch_pipeline_reference.reader import _check_payload, read_transactions


def test_check_payload_accepts_list_of_dicts(
    valid_payload_two_records: list[dict[str, Any]],
) -> None:
    _check_payload(valid_payload_two_records)


def test_check_payload_accepts_empty_list() -> None:
    _check_payload([])


def test_check_payload_raises_when_top_level_is_not_a_list() -> None:
    payload = {
        "transaction_id": "tx-1",
        "created_at": "6/1/2024 8:42:05",
        "amount": 7.49,
        "currency": "EUR",
        "charged_partner": "getland",
        "status": "processed",
    }

    with pytest.raises(
        ValueError,
        match="Expected input JSON to be a list of transaction records.",
    ):
        _check_payload(payload)


def test_check_payload_raises_when_list_contains_non_dict(
    valid_raw_record_1: dict[str, Any],
) -> None:
    payload = [valid_raw_record_1, "not-a-dict"]

    with pytest.raises(
        ValueError,
        match=r"Expected record at index 1 to be a dict object\.",
    ):
        _check_payload(payload)


def test_read_transactions_returns_payload_from_valid_json_file(
    valid_payload: list[dict[str, Any]],
    write_json_file,
) -> None:
    input_path = write_json_file("transactions.json", valid_payload)

    payload = read_transactions(input_path)

    assert payload == valid_payload


def test_read_transactions_logs_read_and_loaded_messages(
    valid_payload_two_records: list[dict[str, Any]],
    write_json_file,
    caplog: pytest.LogCaptureFixture,
) -> None:
    input_path = write_json_file("transactions.json", valid_payload_two_records)

    with caplog.at_level(logging.INFO):
        read_transactions(input_path)

    assert f"Reading transaction file: {input_path}" in caplog.text
    assert "Loaded 2 transaction records" in caplog.text


def test_read_transactions_raises_for_invalid_top_level_json_structure(
    write_json_file,
) -> None:
    invalid_payload = {
        "transaction_id": "tx-1",
        "created_at": "6/1/2024 8:42:05",
        "amount": 7.49,
        "currency": "EUR",
        "charged_partner": "getland",
        "status": "processed",
    }

    input_path = write_json_file("transactions.json", invalid_payload)

    with pytest.raises(
        ValueError,
        match="Expected input JSON to be a list of transaction records.",
    ):
        read_transactions(input_path)


def test_read_transactions_raises_for_invalid_record_type_inside_list(
    valid_raw_record_1: dict[str, Any],
    write_json_file,
) -> None:
    invalid_payload = [valid_raw_record_1, 123]
    input_path = write_json_file("transactions.json", invalid_payload)

    with pytest.raises(
        ValueError,
        match=r"Expected record at index 1 to be a dict object\.",
    ):
        read_transactions(input_path)


def test_read_transactions_propagates_json_decode_error(tmp_path: Path) -> None:
    input_path = tmp_path / "transactions.json"
    input_path.write_text("{not-valid-json", encoding=ENCODING)

    with pytest.raises(json.JSONDecodeError):
        read_transactions(input_path)
