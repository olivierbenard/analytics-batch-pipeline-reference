from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest

from batch_pipeline_reference.config import CSV_HEADER
from batch_pipeline_reference.models import MonthlyPremium
from batch_pipeline_reference.writer import write_output


@pytest.fixture
def sample_rows() -> list[MonthlyPremium]:
    return [
        MonthlyPremium(
            partner="getland",
            month="2024-06-01",
            currency="EUR",
            total_premium=Decimal("15.30"),
        ),
        MonthlyPremium(
            partner="berlinre",
            month="2024-07-01",
            currency="GBP",
            total_premium=Decimal("4.81"),
        ),
    ]


def test_write_output_creates_file(
    tmp_path: Path, sample_rows: list[MonthlyPremium]
) -> None:
    output_path = tmp_path / "output.csv"

    write_output(sample_rows, output_path)

    assert output_path.exists()


def test_write_output_writes_correct_header(
    tmp_path: Path, sample_rows: list[MonthlyPremium]
) -> None:
    output_path = tmp_path / "output.csv"

    write_output(sample_rows, output_path)

    with output_path.open() as f:
        reader = csv.reader(f)
        header = next(reader)

    assert header == ["partner", "month", "currency", "total_premium"]


def test_write_output_uses_default_header_when_none_is_provided(
    tmp_path: Path,
    sample_rows: list[MonthlyPremium],
) -> None:
    output_path = tmp_path / "output.csv"

    write_output(sample_rows, output_path)

    with output_path.open(newline="") as file:
        reader = csv.reader(file)
        header = next(reader)

    assert header == CSV_HEADER


def test_write_output_uses_custom_header_when_provided(
    tmp_path: Path,
    sample_rows: list[MonthlyPremium],
) -> None:
    output_path = tmp_path / "output.csv"
    custom_header = ["a", "b", "c", "d"]

    write_output(sample_rows, output_path, header=custom_header)

    with output_path.open(newline="") as file:
        reader = csv.reader(file)
        header = next(reader)

    assert header == custom_header


def test_write_output_writes_rows_correctly(
    tmp_path: Path, sample_rows: list[MonthlyPremium]
) -> None:
    output_path = tmp_path / "output.csv"

    write_output(sample_rows, output_path)

    with output_path.open() as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        rows = list(reader)

    assert rows == [
        ["getland", "2024-06-01", "EUR", "15.30"],
        ["berlinre", "2024-07-01", "GBP", "4.81"],
    ]


def test_write_output_formats_decimal_to_two_digits(tmp_path: Path) -> None:
    rows = [
        MonthlyPremium(
            partner="getland",
            month="2024-06-01",
            currency="EUR",
            total_premium=Decimal("10"),
        )
    ]

    output_path = tmp_path / "output.csv"

    write_output(rows, output_path)

    with output_path.open() as f:
        reader = csv.reader(f)
        next(reader)
        row = next(reader)

    assert row[3] == "10.00"


def test_write_output_creates_parent_directories(
    tmp_path: Path, sample_rows: list[MonthlyPremium]
) -> None:
    output_path = tmp_path / "nested" / "dir" / "output.csv"

    write_output(sample_rows, output_path)

    assert output_path.exists()


def test_write_output_logs_success(
    tmp_path: Path, sample_rows: list[MonthlyPremium], caplog: pytest.LogCaptureFixture
) -> None:
    output_path = tmp_path / "output.csv"

    with caplog.at_level("INFO"):
        write_output(sample_rows, output_path)

    assert "Wrote output CSV to" in caplog.text


def test_write_output_writes_only_header_when_rows_are_empty(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "output.csv"

    write_output([], output_path)

    with output_path.open(newline="") as file:
        reader = csv.reader(file)
        rows = list(reader)

    assert rows == [CSV_HEADER]
