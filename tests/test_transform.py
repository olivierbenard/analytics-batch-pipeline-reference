from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from batch_pipeline_reference.exceptions import MixedCurrencyError
from batch_pipeline_reference.models import MonthlyPremium, PremiumTransaction
from batch_pipeline_reference.transform import (
    aggregate_monthly_premiums,
    deduplicate_raw_records,
    ensure_single_currency,
    filter_transactions,
    transform_transactions_to_monthly_premiums,
)
from batch_pipeline_reference.validator import TransactionStatus


def test_deduplicate_raw_records_removes_duplicates_and_keeps_first_seen_order() -> (
    None
):
    record_a: dict[str, Any] = {
        "transaction_id": "tx-1",
        "created_at": "6/1/2024 8:42:05",
        "amount": 7.49,
        "currency": "EUR",
        "charged_partner": "getland",
        "status": "processed",
    }
    duplicate_of_a: dict[str, Any] = {
        "status": "processed",
        "charged_partner": "getland",
        "currency": "EUR",
        "amount": 7.49,
        "created_at": "6/1/2024 8:42:05",
        "transaction_id": "tx-1",
    }
    record_b: dict[str, Any] = {
        "transaction_id": "tx-2",
        "created_at": "6/2/2024 9:00:00",
        "amount": 12.10,
        "currency": "GBP",
        "charged_partner": "berlinre",
        "status": "failed",
    }

    result, duplicate_count = deduplicate_raw_records(
        [record_a, duplicate_of_a, record_b]
    )

    assert result == [record_a, record_b]
    assert duplicate_count == 1


def test_deduplicate_raw_records_returns_empty_list_for_empty_input() -> None:
    assert deduplicate_raw_records([]) == ([], 0)


def test_deduplicate_raw_records_keeps_all_records_when_no_duplicates_exist() -> None:
    record_a: dict[str, Any] = {
        "transaction_id": "tx-1",
        "created_at": "6/1/2024 8:42:05",
        "amount": 7.49,
        "currency": "EUR",
        "charged_partner": "getland",
        "status": "processed",
    }
    record_b: dict[str, Any] = {
        "transaction_id": "tx-2",
        "created_at": "6/2/2024 9:00:00",
        "amount": 12.10,
        "currency": "GBP",
        "charged_partner": "berlinre",
        "status": "failed",
    }

    result, duplicate_count = deduplicate_raw_records([record_a, record_b])

    assert result == [record_a, record_b]
    assert duplicate_count == 0


@pytest.fixture
def processed_eur_record_a_june() -> PremiumTransaction:
    return PremiumTransaction(
        transaction_id="tx-1",
        created_at=datetime(2024, 6, 1, 8, 42, 5),
        month="2024-06-01",
        amount=Decimal("10.10"),
        currency="EUR",
        charged_partner="getland",
        status="processed",
    )


@pytest.fixture
def processed_eur_record_b_june() -> PremiumTransaction:
    return PremiumTransaction(
        transaction_id="tx-2",
        created_at=datetime(2024, 6, 15, 10, 0, 0),
        month="2024-06-01",
        amount=Decimal("5.20"),
        currency="EUR",
        charged_partner="getland",
        status="processed",
    )


@pytest.fixture
def processed_gbp_record_june() -> PremiumTransaction:
    return PremiumTransaction(
        transaction_id="tx-3",
        created_at=datetime(2024, 6, 20, 12, 0, 0),
        month="2024-06-01",
        amount=Decimal("3.50"),
        currency="GBP",
        charged_partner="getland",
        status="processed",
    )


@pytest.fixture
def refunded_eur_record_june() -> PremiumTransaction:
    return PremiumTransaction(
        transaction_id="tx-4",
        created_at=datetime(2024, 6, 25, 9, 0, 0),
        month="2024-06-01",
        amount=Decimal("100.00"),
        currency="EUR",
        charged_partner="getland",
        status="refunded",
    )


@pytest.fixture
def failed_eur_record_july() -> PremiumTransaction:
    return PremiumTransaction(
        transaction_id="tx-5",
        created_at=datetime(2024, 7, 1, 9, 0, 0),
        month="2024-07-01",
        amount=Decimal("12.00"),
        currency="EUR",
        charged_partner="berlinre",
        status="failed",
    )


def test_filter_transactions_keeps_only_requested_status(
    processed_eur_record_a_june: PremiumTransaction,
    refunded_eur_record_june: PremiumTransaction,
    failed_eur_record_july: PremiumTransaction,
) -> None:
    records = [
        processed_eur_record_a_june,
        refunded_eur_record_june,
        failed_eur_record_july,
    ]

    result = filter_transactions(records, status=TransactionStatus.PROCESSED)

    assert result == [processed_eur_record_a_june]


def test_filter_transactions_returns_empty_list_when_no_match(
    refunded_eur_record_june: PremiumTransaction,
    failed_eur_record_july: PremiumTransaction,
) -> None:
    records = [refunded_eur_record_june, failed_eur_record_july]

    result = filter_transactions(records, status=TransactionStatus.PROCESSED)

    assert result == []


def test_ensure_single_currency_returns_currency_for_uniform_input(
    processed_eur_record_a_june: PremiumTransaction,
    processed_eur_record_b_june: PremiumTransaction,
) -> None:
    records = [processed_eur_record_a_june, processed_eur_record_b_june]

    result = ensure_single_currency(records)

    assert result == "EUR"


def test_ensure_single_currency_raises_on_empty_input() -> None:
    with pytest.raises(
        MixedCurrencyError,
        match="No records available to determine a single aggregation currency.",
    ):
        ensure_single_currency([])


def test_ensure_single_currency_raises_on_multiple_currencies(
    processed_eur_record_a_june: PremiumTransaction,
    processed_gbp_record_june: PremiumTransaction,
) -> None:
    records = [processed_eur_record_a_june, processed_gbp_record_june]

    with pytest.raises(
        MixedCurrencyError,
        match=r"Expected a single currency for aggregation, found: \['EUR', 'GBP'\]",
    ):
        ensure_single_currency(records)


def test_aggregate_monthly_premiums_groups_by_partner_month_and_currency(
    processed_eur_record_a_june: PremiumTransaction,
    processed_eur_record_b_june: PremiumTransaction,
    processed_gbp_record_june: PremiumTransaction,
) -> None:
    records = [
        processed_eur_record_a_june,
        processed_eur_record_b_june,
        processed_gbp_record_june,
    ]

    result = aggregate_monthly_premiums(records)

    assert result == [
        MonthlyPremium(
            partner="getland",
            month="2024-06-01",
            currency="EUR",
            total_premium=Decimal("15.30"),
        ),
        MonthlyPremium(
            partner="getland",
            month="2024-06-01",
            currency="GBP",
            total_premium=Decimal("3.50"),
        ),
    ]


def test_aggregate_monthly_premiums_returns_sorted_rows() -> None:
    records = [
        PremiumTransaction(
            transaction_id="tx-10",
            created_at=datetime(2024, 7, 1, 9, 0, 0),
            month="2024-07-01",
            amount=Decimal("2.00"),
            currency="EUR",
            charged_partner="liadigital",
            status="processed",
        ),
        PremiumTransaction(
            transaction_id="tx-11",
            created_at=datetime(2024, 6, 1, 9, 0, 0),
            month="2024-06-01",
            amount=Decimal("1.00"),
            currency="EUR",
            charged_partner="berlinre",
            status="processed",
        ),
        PremiumTransaction(
            transaction_id="tx-12",
            created_at=datetime(2024, 6, 1, 9, 0, 0),
            month="2024-06-01",
            amount=Decimal("3.00"),
            currency="GBP",
            charged_partner="berlinre",
            status="processed",
        ),
    ]

    result = aggregate_monthly_premiums(records)

    assert [(row.partner, row.month, row.currency) for row in result] == [
        ("berlinre", "2024-06-01", "EUR"),
        ("berlinre", "2024-06-01", "GBP"),
        ("liadigital", "2024-07-01", "EUR"),
    ]


def test_transform_transactions_to_monthly_premiums_filters_and_aggregates(
    processed_eur_record_a_june: PremiumTransaction,
    processed_eur_record_b_june: PremiumTransaction,
    refunded_eur_record_june: PremiumTransaction,
) -> None:
    records = [
        processed_eur_record_a_june,
        processed_eur_record_b_june,
        refunded_eur_record_june,
    ]

    result = transform_transactions_to_monthly_premiums(records)

    assert result == [
        MonthlyPremium(
            partner="getland",
            month="2024-06-01",
            currency="EUR",
            total_premium=Decimal("15.30"),
        )
    ]


def test_transform_transactions_to_monthly_premiums_raises_on_multiple_currencies_by_default(
    processed_eur_record_a_june: PremiumTransaction,
    processed_gbp_record_june: PremiumTransaction,
) -> None:
    records = [processed_eur_record_a_june, processed_gbp_record_june]

    with pytest.raises(MixedCurrencyError):
        transform_transactions_to_monthly_premiums(records)


def test_transform_transactions_to_monthly_premiums_logs_warning_and_aggregates_when_multiple_currencies_allowed(
    processed_eur_record_a_june: PremiumTransaction,
    processed_gbp_record_june: PremiumTransaction,
    caplog: pytest.LogCaptureFixture,
) -> None:
    records = [processed_eur_record_a_june, processed_gbp_record_june]

    with caplog.at_level(logging.WARNING):
        result = transform_transactions_to_monthly_premiums(
            records,
            fail_on_multiple_currencies=False,
        )

    assert "Multiple currencies detected in filtered records" in caplog.text
    assert result == [
        MonthlyPremium(
            partner="getland",
            month="2024-06-01",
            currency="EUR",
            total_premium=Decimal("10.10"),
        ),
        MonthlyPremium(
            partner="getland",
            month="2024-06-01",
            currency="GBP",
            total_premium=Decimal("3.50"),
        ),
    ]


def test_transform_transactions_to_monthly_premiums_can_filter_another_status(
    processed_eur_record_a_june: PremiumTransaction,
    refunded_eur_record_june: PremiumTransaction,
) -> None:
    records = [processed_eur_record_a_june, refunded_eur_record_june]

    result = transform_transactions_to_monthly_premiums(
        records,
        status=TransactionStatus.REFUNDED,
    )

    assert result == [
        MonthlyPremium(
            partner="getland",
            month="2024-06-01",
            currency="EUR",
            total_premium=Decimal("100.00"),
        )
    ]
