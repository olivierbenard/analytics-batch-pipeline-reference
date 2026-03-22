from pathlib import Path

import pytest

from batch_pipeline_reference.config import ENCODING
from batch_pipeline_reference.main import run_batch_job


@pytest.mark.e2e
def test_end_to_end(tmp_path: Path, caplog) -> None:
    input_path = tmp_path / "input.json"
    output_path = tmp_path / "output" / "monthly_partner_premiums.csv"

    input_path.write_text(
        """
[
  {
    "transaction_id": "1",
    "created_at": "7/2/2024 18:21:49",
    "amount": "4.80",
    "currency": "EUR",
    "charged_partner": "Partner A",
    "status": "processed"
  },
  {
    "transaction_id": "2",
    "created_at": "7/10/2024 10:00:00",
    "amount": "5.20",
    "currency": "EUR",
    "charged_partner": "Partner A",
    "status": "processed"
  },
  {
    "transaction_id": "3",
    "created_at": "7/12/2024 09:00:00",
    "amount": "100.00",
    "currency": "EUR",
    "charged_partner": "Partner A",
    "status": "failed"
  },
  {
    "transaction_id": "4",
    "created_at": "7/12/2024 09:00:00",
    "amount": "100.00",
    "currency": "EUR",
    "charged_partner": "Partner A",
    "status": "process"
  },
  {
    "transaction_id": "5",
    "created_at": "7/12/2024 09:00:00",
    "amount": "100.00",
    "currency": "GBP",
    "charged_partner": "Partner A",
    "status": "processed"
  }
]
""".strip(),
        encoding=ENCODING,
    )

    with caplog.at_level("DEBUG"):
        run_batch_job(input_path=input_path, output_path=output_path)

    assert (
        any("Loaded 5 transaction records" in message for message in caplog.messages)
        is True
    )
    assert (
        any(
            "ValidationSummary(total_records=5, valid_records=4, invalid_records=1)"
            in message
            for message in caplog.messages
        )
        is True
    )
    assert (
        any(
            "Detected 1 invalid records during validation" in message
            for message in caplog.messages
        )
        is True
    )
    assert (
        any(
            "Proceeding with 4 validated transactions" in message
            for message in caplog.messages
        )
        is True
    )
    assert (
        any(
            "Multiple currencies detected in filtered records: ['EUR', 'GBP']. Aggregating separately by currency."
            in message
            for message in caplog.messages
        )
        is True
    )
    assert (
        any(
            "Computed 2 aggregated output rows." in message
            for message in caplog.messages
        )
        is True
    )
    assert any("Wrote output CSV" in message for message in caplog.messages) is True

    assert output_path.exists()
    assert (
        output_path.read_text(encoding=ENCODING).strip()
        == "partner,month,currency,total_premium\nPartner A,2024-07-01,EUR,10.00\nPartner A,2024-07-01,GBP,100.00"
    )
