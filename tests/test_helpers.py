from __future__ import annotations

import hashlib
import json
from typing import Any

from batch_pipeline_reference.config import ENCODING
from batch_pipeline_reference.helpers import compute_payload_hash


def test_compute_payload_hash_is_deterministic_for_same_record_content() -> None:
    record_a: dict[str, Any] = {
        "transaction_id": "tx-1",
        "created_at": "6/1/2024 8:42:05",
        "amount": 7.49,
        "currency": "EUR",
        "charged_partner": "getland",
        "status": "processed",
    }
    record_b: dict[str, Any] = {
        "status": "processed",
        "charged_partner": "getland",
        "currency": "EUR",
        "amount": 7.49,
        "created_at": "6/1/2024 8:42:05",
        "transaction_id": "tx-1",
    }

    assert compute_payload_hash(record_a) == compute_payload_hash(record_b)


def test_compute_payload_hash_matches_expected_sha256_of_canonical_json() -> None:
    record: dict[str, Any] = {
        "transaction_id": "tx-1",
        "created_at": "6/1/2024 8:42:05",
        "amount": 7.49,
        "currency": "EUR",
        "charged_partner": "getland",
        "status": "processed",
    }

    canonical_json = json.dumps(record, sort_keys=True, separators=(",", ":"))
    expected_hash = hashlib.sha256(canonical_json.encode(ENCODING)).hexdigest()

    assert compute_payload_hash(record) == expected_hash


def test_compute_payload_hash_differs_for_different_records() -> None:
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
        "created_at": "6/1/2024 8:42:05",
        "amount": 7.49,
        "currency": "EUR",
        "charged_partner": "getland",
        "status": "processed",
    }

    assert compute_payload_hash(record_a) != compute_payload_hash(record_b)
