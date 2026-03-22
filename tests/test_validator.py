from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from batch_pipeline_reference.exceptions import InvalidRecordError
from batch_pipeline_reference.models import (
    PremiumTransaction,
    ValidationResult,
)
from batch_pipeline_reference.validator import (
    month_start_as_string,
    validate_amount,
    validate_and_normalise_record,
    validate_and_normalise_records,
    validate_created_at,
    validate_currency,
    validate_status,
    validate_transaction_id,
)


@pytest.fixture
def reference_date() -> datetime:
    return datetime(2024, 6, 10, tzinfo=timezone.utc)


def test_month_start_as_string_returns_first_day_of_month() -> None:
    dt = datetime(2026, 3, 14, 15, 30, 45)

    result = month_start_as_string(dt)

    assert result == "2026-03-01"


def test_validate_transaction_id_returns_stripped_value() -> None:
    result = validate_transaction_id("  tx-123  ")

    assert result == "tx-123"


def test_validate_transaction_id_raises_for_empty_value() -> None:
    with pytest.raises(
        InvalidRecordError,
        match="transaction_id must be a non-empty string.",
    ):
        validate_transaction_id("   ")


def test_validate_currency_normalizes_to_uppercase() -> None:
    result = validate_currency(" eur ")

    assert result == "EUR"


@pytest.mark.parametrize("invalid_currency", ["EU", "EURO", "€", "12A", ""])
def test_validate_currency_raises_for_invalid_values(invalid_currency: str) -> None:
    with pytest.raises(
        InvalidRecordError,
        match=r"Invalid currency '.+'. Expected ISO format like 'EUR'.|Invalid currency ''. Expected ISO format like 'EUR'.",
    ):
        validate_currency(invalid_currency)


def test_validate_status_normalizes_to_lowercase() -> None:
    result = validate_status(" Processed ")

    assert result == "processed"


def test_validate_status_raises_for_unknown_status() -> None:
    with pytest.raises(
        InvalidRecordError,
        match="Unknown transaction status: process",
    ):
        validate_status("process")


def test_validate_amount_returns_decimal_for_valid_input() -> None:
    result = validate_amount("7.49")

    assert result == Decimal("7.49")


@pytest.mark.parametrize("amount", ["abc", None])
def test_validate_amount_raises_for_non_numeric_values(amount: object) -> None:
    with pytest.raises(
        InvalidRecordError,
        match=r"Invalid amount '.+'. Must be numeric.|Invalid amount 'None'. Must be numeric.",
    ):
        validate_amount(amount)  # type: ignore[arg-type]


def test_validate_amount_raises_for_negative_when_positive_only_true() -> None:
    with pytest.raises(
        InvalidRecordError,
        match="amount cannot be negative",
    ):
        validate_amount("-1.00", positive_only=True)


def test_validate_created_at_parses_valid_timestamp(reference_date: datetime) -> None:
    result = validate_created_at(
        "6/1/2024 8:42:05",
        reference_date=reference_date,
    )

    assert result == datetime(2024, 6, 1, 8, 42, 5)


def test_validate_created_at_raises_for_invalid_format(
    reference_date: datetime,
) -> None:
    with pytest.raises(
        InvalidRecordError,
        match="Invalid created_at '2024-06-01'. Expected format MM/DD/YYYY HH:MM:SS",
    ):
        validate_created_at(
            "2024-06-01",
            reference_date=reference_date,
        )


def test_validate_created_at_raises_for_future_date() -> None:
    with pytest.raises(
        InvalidRecordError,
        match="created_at cannot be in the future",
    ):
        validate_created_at(
            "6/20/2024 8:42:05",
            reference_date=datetime(2024, 6, 10, tzinfo=timezone.utc),
        )


def test_validate_and_normalise_record_returns_normalized_model(
    valid_raw_record_3: dict[str, Any],
) -> None:
    result = validate_and_normalise_record(valid_raw_record_3)

    assert result == PremiumTransaction(
        transaction_id="tx-3",
        created_at=datetime(2024, 6, 3, 8, 42, 5),
        month="2024-06-01",
        amount=Decimal("7.49"),
        currency="EUR",
        charged_partner="getland",
        status="processed",
    )


def test_validate_and_normalise_record_raises_for_missing_fields() -> None:
    record = {
        "transaction_id": "tx-1",
        "created_at": "6/1/2024 8:42:05",
        "amount": "7.49",
        "currency": "EUR",
        # charged_partner missing
        "status": "processed",
    }

    with pytest.raises(
        InvalidRecordError,
        match=r"Missing required fields: charged_partner",
    ):
        validate_and_normalise_record(record)


def test_validate_and_normalise_record_raises_for_empty_charged_partner(
    valid_raw_record_3: dict[str, Any],
) -> None:
    record = dict(valid_raw_record_3)
    record["charged_partner"] = "   "

    with pytest.raises(
        InvalidRecordError,
        match="charged_partner must not be empty.",
    ):
        validate_and_normalise_record(record)


def test_validate_and_normalise_record_raises_for_invalid_status(
    valid_raw_record_3: dict[str, Any],
) -> None:
    record = dict(valid_raw_record_3)
    record["status"] = "process"

    with pytest.raises(
        InvalidRecordError,
        match="Unknown transaction status: process",
    ):
        validate_and_normalise_record(record)


def test_validate_and_normalise_records_returns_summary_and_invalid_records(
    valid_raw_record_3: dict[str, Any],
) -> None:
    invalid_record = dict(valid_raw_record_3)
    invalid_record["status"] = "process"

    records = [valid_raw_record_3, invalid_record]

    result = validate_and_normalise_records(records)

    assert isinstance(result, ValidationResult)
    assert result.summary.total_records == 2
    assert result.summary.valid_records == 1
    assert result.summary.invalid_records == 1
    assert result.has_invalid_records() is True

    assert len(result.valid_records) == 1
    assert len(result.invalid_records) == 1
    assert result.invalid_records[0].record == invalid_record
    assert result.invalid_records[0].error == "Unknown transaction status: process"


def test_validate_and_normalise_records_returns_no_invalid_records_for_valid_input(
    valid_raw_record_3: dict[str, Any],
) -> None:
    records = [valid_raw_record_3]

    result = validate_and_normalise_records(records)

    assert result.summary.total_records == 1
    assert result.summary.valid_records == 1
    assert result.summary.invalid_records == 0
    assert result.has_invalid_records() is False
    assert result.invalid_records == []


def test_validate_and_normalise_records_keeps_order_of_valid_records() -> None:
    records = [
        {
            "transaction_id": "tx-1",
            "created_at": "6/1/2024 8:42:05",
            "amount": "7.49",
            "currency": "EUR",
            "charged_partner": "getland",
            "status": "processed",
        },
        {
            "transaction_id": "tx-2",
            "created_at": "7/1/2024 8:42:05",
            "amount": "9.99",
            "currency": "GBP",
            "charged_partner": "berlinre",
            "status": "failed",
        },
    ]

    result = validate_and_normalise_records(records)

    assert [record.transaction_id for record in result.valid_records] == [
        "tx-1",
        "tx-2",
    ]


def test_validation_summary_matches_result_lists(
    valid_raw_record_3: dict[str, Any],
) -> None:
    invalid_record = dict(valid_raw_record_3)
    invalid_record["status"] = "process"

    result = validate_and_normalise_records([valid_raw_record_3, invalid_record])

    assert result.summary.valid_records == len(result.valid_records)
    assert result.summary.invalid_records == len(result.invalid_records)
    assert result.summary.total_records == (
        len(result.valid_records) + len(result.invalid_records)
    )
