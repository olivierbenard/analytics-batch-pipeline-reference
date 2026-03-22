"""
Output writing utilities for the premium batch job.

This module writes aggregated monthly premium results to CSV files using
a stable schema suitable for downstream reporting and analysis.
"""

from __future__ import annotations

import csv
from pathlib import Path

from batch_pipeline_reference import logger
from batch_pipeline_reference.config import CSV_HEADER, ENCODING
from batch_pipeline_reference.models import MonthlyPremium


def write_output(
    rows: list[MonthlyPremium], output_path: Path, header: list[str] | None = None
) -> None:
    """
    Write aggregated monthly premium rows to a CSV file.

    The output file is created using the configured text encoding.
    Parent directories are created automatically if they do not exist.

    Parameters
    ----------
    rows : list[MonthlyPremium]
        Aggregated monthly premium rows to serialize.
    output_path : Path
        Destination path of the CSV output file.
    header : list[str] | None, default=None
        Optional CSV header. If not provided, the default project header
        is used.
    """
    if header is None:
        header = CSV_HEADER

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding=ENCODING, newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for row in rows:
            writer.writerow(
                [
                    row.partner,
                    row.month,
                    row.currency,
                    f"{row.total_premium:.2f}",
                ]
            )
    logger.info("Wrote output CSV to %s", output_path)
