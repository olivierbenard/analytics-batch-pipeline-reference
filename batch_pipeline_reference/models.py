"""
Domain models for the premium batch job.

This module defines the typed data structures used across the pipeline,
including normalized transactions, invalid records, validation summaries,
and aggregated monthly premiums.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class TransactionStatus(StrEnum):
    """
    Enumeration of the supported transaction processing statuses.

    These values represent the lifecycle state of a transaction
    after it has been processed by the upstream system.
    """

    PROCESSED = "processed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class PremiumTransaction:
    """
    Normalized transaction record used throughout the pipeline.

    Instances of this model are produced after the validation and
    normalization stage. At this point, all fields have been checked
    for correctness and converted to strongly typed values.

    Attributes
    ----------
    transaction_id : str
        Unique identifier of the transaction.
    created_at : datetime
        Timestamp when the transaction occurred.
    month : str
        Normalized month identifier (`YYYY-MM-01`) used for
        aggregation purposes.
    amount : Decimal
        Transaction premium amount.
    currency : str
        ISO 4217 currency code (e.g. EUR, GBP).
    charged_partner : str
        Partner responsible for the charged premium.
    status : str
        Processing status of the transaction.
    """

    transaction_id: str
    created_at: datetime
    month: str
    amount: Decimal
    currency: str
    charged_partner: str
    status: str


@dataclass(frozen=True)
class InvalidRecord:
    """
    Representation of a raw input record that failed validation.

    Instances of this model capture both the original record and
    the validation error encountered during parsing or normalization.

    Attributes
    ----------
    record : dict[str, Any]
        Original raw transaction record.
    error : str
        Human-readable description of the validation failure.
    """

    record: dict[str, Any]
    error: str


@dataclass(frozen=True)
class ValidationSummary:
    """
    Summary statistics produced after the validation stage.

    This model provides a quick overview of how many records were
    successfully parsed and how many were rejected.

    Attributes
    ----------
    total_records : int
        Total number of input records processed.
    valid_records : int
        Number of records successfully validated.
    invalid_records : int
        Number of records rejected due to validation errors.
    """

    total_records: int
    valid_records: int
    invalid_records: int


@dataclass(frozen=True)
class ValidationResult:
    """
    Result of the batch validation process.

    This model aggregates all successfully validated transactions,
    the rejected records, and a summary of the validation outcome.

    Attributes
    ----------
    valid_records : list[PremiumTransaction]
        Successfully validated and normalized transactions.
    invalid_records : list[InvalidRecord]
        Records that failed validation.
    summary : ValidationSummary
        Aggregated validation statistics.
    """

    valid_records: list[PremiumTransaction]
    invalid_records: list[InvalidRecord]
    summary: ValidationSummary

    def has_invalid_records(self) -> bool:
        """
        Return True if the validation process produced invalid records.
        """
        return len(self.invalid_records) > 0


@dataclass(frozen=True)
class MonthlyPremium:
    """
    Aggregated monthly premium for a partner and currency.

    This model represents the final business output of the pipeline,
    produced after grouping validated transactions by partner,
    month, and currency.

    Attributes
    ----------
    partner : str
        Partner responsible for the premiums.
    month : str
        Aggregation month in `YYYY-MM-01` format.
    currency : str
        Currency of the aggregated premiums.
    total_premium : Decimal
        Total premium amount for the given partner, month, and currency.
    """

    partner: str
    month: str
    currency: str
    total_premium: Decimal
