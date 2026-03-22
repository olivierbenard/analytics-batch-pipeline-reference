from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from batch_pipeline_reference.models import (
    InvalidRecord,
    PremiumTransaction,
    ValidationResult,
    ValidationSummary,
)

# fixtures used in test_reader.py:


@pytest.fixture
def valid_raw_record_1() -> dict[str, Any]:
    return {
        "transaction_id": "tx-1",
        "created_at": "6/1/2024 8:42:05",
        "amount": 7.49,
        "currency": "EUR",
        "charged_partner": "getland",
        "status": "processed",
    }


@pytest.fixture
def valid_raw_record_2() -> dict[str, Any]:
    return {
        "transaction_id": "tx-2",
        "created_at": "6/2/2024 9:00:00",
        "amount": 12.10,
        "currency": "GBP",
        "charged_partner": "berlinre",
        "status": "failed",
    }


@pytest.fixture
def valid_raw_record_3() -> dict[str, Any]:
    return {
        "transaction_id": " tx-3 ",
        "created_at": "6/3/2024 8:42:05",
        "amount": "7.49",
        "currency": " eur ",
        "charged_partner": " getland ",
        "status": " processed ",
    }


@pytest.fixture
def valid_payload(
    valid_raw_record_1: dict[str, Any],
) -> list[dict[str, Any]]:
    return [valid_raw_record_1]


@pytest.fixture
def valid_payload_two_records(
    valid_raw_record_1: dict[str, Any],
    valid_raw_record_2: dict[str, Any],
) -> list[dict[str, Any]]:
    return [valid_raw_record_1, valid_raw_record_2]


@pytest.fixture
def write_json_file(tmp_path: Path):
    def _write(filename: str, payload: Any) -> Path:
        path = tmp_path / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    return _write


# fixtures used in test_validation_result.py


@pytest.fixture
def valid_transaction() -> PremiumTransaction:
    """
    Return an valid transaction.
    """
    return PremiumTransaction(
        transaction_id="tx-1",
        created_at=datetime(2024, 6, 1, 8, 42, 5),
        month="2024-06-01",
        amount=Decimal("7.49"),
        currency="EUR",
        charged_partner="getland",
        status="processed",
    )


@pytest.fixture
def invalid_record() -> InvalidRecord:
    """
    Return an invalid record.
    """
    return InvalidRecord(
        record={
            "transaction_id": "tx-invalid",
            "created_at": "6/1/2024 8:42:05",
            "amount": 7.49,
            "currency": "EUR",
            "charged_partner": "getland",
            "status": "process",
        },
        error="Unknown transaction status: process",
    )


@pytest.fixture
def validation_summary_valid_only() -> ValidationSummary:
    """
    Return the summary corresponding to 1 valid record and 0 invalid.
    """
    return ValidationSummary(
        total_records=1,
        valid_records=1,
        invalid_records=0,
    )


@pytest.fixture
def validation_summary_with_invalid() -> ValidationSummary:
    """
    Return the summary corresponding to 1 valid record and 1 invalid.
    """
    return ValidationSummary(
        total_records=2,
        valid_records=1,
        invalid_records=1,
    )


@pytest.fixture
def validation_result_valid_only(
    valid_transaction: PremiumTransaction,
    validation_summary_valid_only: ValidationSummary,
) -> ValidationResult:
    """
    Return a result with 1 valid transaction and 0 invalid.
    """
    return ValidationResult(
        valid_records=[valid_transaction],
        invalid_records=[],
        summary=validation_summary_valid_only,
    )


@pytest.fixture
def validation_result_with_invalid(
    valid_transaction: PremiumTransaction,
    invalid_record: InvalidRecord,
    validation_summary_with_invalid: ValidationSummary,
) -> ValidationResult:
    """
    Return a result with 1 valid transaction and 1 invalid.
    """
    return ValidationResult(
        valid_records=[valid_transaction],
        invalid_records=[invalid_record],
        summary=validation_summary_with_invalid,
    )
