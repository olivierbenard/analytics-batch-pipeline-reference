"""
Business transformation logic for the premium batch job.

This module filters validated transactions, applies aggregation rules,
and produces monthly premium outputs grouped by partner, month, and
currency.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from batch_pipeline_reference import logger
from batch_pipeline_reference.exceptions import MixedCurrencyError
from batch_pipeline_reference.helpers import compute_payload_hash
from batch_pipeline_reference.models import (
    MonthlyPremium,
    PremiumTransaction,
)
from batch_pipeline_reference.validator import TransactionStatus


def deduplicate_raw_records(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """
    Deduplicate raw records using a deterministic payload hash.

    Records are kept in first-seen order.
    """
    seen_hashes: set[str] = set()
    deduplicated_records: list[dict[str, Any]] = []
    duplicate_count: int = 0

    for record in records:
        payload_hash = compute_payload_hash(record)
        if payload_hash in seen_hashes:
            duplicate_count += 1
            continue
        seen_hashes.add(payload_hash)
        deduplicated_records.append(record)

    return deduplicated_records, duplicate_count


def filter_transactions(
    records: list[PremiumTransaction],
    status: TransactionStatus,
) -> list[PremiumTransaction]:
    """
    Filter normalized transaction records by status.

    Parameters
    ----------
    records : list[PremiumTransaction]
        Normalized transaction records.
    status : TransactionStatus
        Target status to retain.

    Returns
    -------
    list[PremiumTransaction]
        Filtered transaction records matching the requested status.
    """
    return [record for record in records if record.status == status.value]


def ensure_single_currency(records: list[PremiumTransaction]) -> str:
    """
    Ensure that all provided records share the same currency.

    This is important because the output format does not include a
    currency column, so aggregating across multiple currencies would
    be ambiguous.

    Parameters
    ----------
    records : list[PremiumTransaction]
        Transaction records to inspect.

    Returns
    -------
    str
        The single currency present in the records.

    Raises
    ------
    MixedCurrencyError
        If the input contains zero records or more than one currency.
    """
    currencies = sorted({record.currency for record in records})

    if not records:
        raise MixedCurrencyError(
            "No records available to determine a single aggregation currency."
        )

    if len(currencies) > 1:
        raise MixedCurrencyError(
            f"Expected a single currency for aggregation, found: {currencies}"
        )

    return currencies[0]


def aggregate_monthly_premiums(
    records: list[PremiumTransaction],
) -> list[MonthlyPremium]:
    """
    Aggregate monthly total premiums by partner.

    Records are grouped by:
    - charged_partner
    - month
    - currency

    Amounts are summed using Decimal to preserve financial precision.

    Parameters
    ----------
    records : list[PremiumTransaction]
        Filtered normalized transaction records.

    Returns
    -------
    list[MonthlyPremium]
        Aggregated monthly premiums sorted by partner and month.
    """
    grouped: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0.00"))

    for record in records:
        key = (record.charged_partner, record.month, record.currency)
        grouped[key] += record.amount

    aggregated_rows = [
        MonthlyPremium(
            partner=partner,
            month=month,
            currency=currency,
            total_premium=total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )
        for (partner, month, currency), total in grouped.items()
    ]

    return sorted(
        aggregated_rows, key=lambda row: (row.partner, row.month, row.currency)
    )


def transform_transactions_to_monthly_premiums(
    records: list[PremiumTransaction],
    status: TransactionStatus = TransactionStatus.PROCESSED,
    fail_on_multiple_currencies: bool = True,
) -> list[MonthlyPremium]:
    """
    End-to-end business transformation for normalized records.

    The transformation performs the following steps:
    1. Filter records by the requested transaction status.
    2. Ensure aggregation happens on a single currency.
    3. Aggregate monthly total premiums per partner.

    Parameters
    ----------
    records : list[PremiumTransaction]
        Validated and normalized transaction records.
    status : TransactionStatus, default=TransactionStatus.PROCESSED
        Transaction status to include in the aggregation.

    Returns
    -------
    list[MonthlyPremium]
        Aggregated monthly premium rows.
    """
    filtered_records = filter_transactions(records, status=status)
    if fail_on_multiple_currencies:
        ensure_single_currency(filtered_records)
    currencies = sorted({record.currency for record in filtered_records})
    if len(currencies) > 1:
        logger.warning(
            "Multiple currencies detected in filtered records: %s. "
            "Aggregating separately by currency.",
            currencies,
        )
    return aggregate_monthly_premiums(filtered_records)
