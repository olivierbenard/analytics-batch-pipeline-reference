"""
Validation and normalization utilities for the premium batch job.

This module validates raw input records, normalizes their fields into
strongly typed values, and produces structured validation results for
downstream transformation steps.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from batch_pipeline_reference.exceptions import InvalidRecordError
from batch_pipeline_reference.models import (
    InvalidRecord,
    PremiumTransaction,
    TransactionStatus,
    ValidationResult,
    ValidationSummary,
)

INPUT_DATETIME_FORMAT: str = "%m/%d/%Y %H:%M:%S"
ISO_CURRENCY_PATTERN: re.Pattern = re.compile(r"^[A-Z]{3}$")

REQUIRED_FIELDS: set[str] = {
    "transaction_id",
    "created_at",
    "amount",
    "currency",
    "charged_partner",
    "status",
}


def month_start_as_string(dt: datetime) -> str:
    """
    >>> month_start_as_string(datetime(2026,1,1))
    '2026-01-01'
    """
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime(
        "%Y-%m-%d"
    )


def validate_transaction_id(transaction_id: str) -> str:
    """
    Ensure the transaction identifier is non-empty.
    """
    normalised = transaction_id.strip()
    if not normalised:
        raise InvalidRecordError("transaction_id must be a non-empty string.")
    return normalised


def validate_currency(currency: str) -> str:
    """
    Normalize and validate currency.

    Ensures the currency is a valid ISO 4217 style code (3 uppercase letters).
    Returns the normalized uppercase value.
    """
    normalised = currency.strip().upper()
    if not ISO_CURRENCY_PATTERN.match(normalised):
        raise InvalidRecordError(
            f"Invalid currency '{currency}'. Expected ISO format like 'EUR'."
        )
    return normalised


def validate_status(status: str) -> str:
    """
    Normalize and validate the status.
    """
    normalised = status.strip().lower()
    try:
        TransactionStatus(normalised)
    except ValueError as exception:
        raise InvalidRecordError(f"Unknown transaction status: {status}") from exception
    return normalised


def validate_amount(amount: str | float | int, positive_only: bool = False) -> Decimal:
    """
    Validate and convert the transaction amount to Decimal.
    """
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError) as exception:
        raise InvalidRecordError(
            f"Invalid amount '{amount}'. Must be numeric."
        ) from exception

    if positive_only and value < Decimal("0"):
        raise InvalidRecordError("amount cannot be negative")

    return value


def validate_created_at(
    created_at: str, reference_date: datetime | None = None
) -> datetime:
    """
    Validate and parse the transaction timestamp.

    Expected format: MM/DD/YYYY HH:MM:SS

    Returns
    -------
    datetime
        Parsed datetime object.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    try:
        parsed: datetime = datetime.strptime(created_at.strip(), INPUT_DATETIME_FORMAT)
    except ValueError as exception:
        raise InvalidRecordError(
            f"Invalid created_at '{created_at}'. Expected format MM/DD/YYYY HH:MM:SS"
        ) from exception

    parsed_utc = parsed.replace(tzinfo=timezone.utc)

    if parsed_utc > reference_date:
        raise InvalidRecordError("created_at cannot be in the future")

    return parsed


def validate_and_normalise_record(record: dict[str, Any]) -> PremiumTransaction:
    """
    Methods validating the record present in the input file.
    Amount being financial values, using Decimal is the right
    choice for money aggregation.
    """
    missing_fields = REQUIRED_FIELDS.difference(record.keys())
    if missing_fields:
        raise InvalidRecordError(
            f"Missing required fields: {', '.join(sorted(missing_fields))}"
        )

    transaction_id = validate_transaction_id(str(record["transaction_id"]))
    created_at = validate_created_at(str(record["created_at"]))
    amount = validate_amount(record["amount"])
    currency = validate_currency(str(record["currency"]))

    charged_partner = str(record["charged_partner"]).strip()
    if not charged_partner:
        raise InvalidRecordError("charged_partner must not be empty.")

    status = validate_status(str(record["status"]))

    return PremiumTransaction(
        transaction_id=transaction_id,
        created_at=created_at,
        month=month_start_as_string(created_at),  # allow to group transactions by month
        amount=amount,
        currency=currency,
        charged_partner=charged_partner,
        status=status,
    )


def validate_and_normalise_records(
    records: list[dict[str, Any]],
) -> ValidationResult:
    """
    Iterate through the records, validate and
    normalise the records.
    """
    valid_records: list[PremiumTransaction] = []
    invalid_records: list[InvalidRecord] = []

    for record in records:
        try:
            valid_records.append(validate_and_normalise_record(record))
        except InvalidRecordError as exc:
            invalid_records.append(
                InvalidRecord(
                    record=record,
                    error=str(exc),
                )
            )

    summary = ValidationSummary(
        total_records=len(records),
        valid_records=len(valid_records),
        invalid_records=len(invalid_records),
    )

    return ValidationResult(
        valid_records=valid_records,
        invalid_records=invalid_records,
        summary=summary,
    )
