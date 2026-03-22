"""
Command-line entrypoint for the premium batch job.

This module parses runtime arguments and orchestrates the end-to-end
execution of the batch pipeline from input file to output CSV.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from batch_pipeline_reference import logger
from batch_pipeline_reference.models import (
    MonthlyPremium,
    TransactionStatus,
    ValidationResult,
)
from batch_pipeline_reference.reader import read_transactions
from batch_pipeline_reference.transform import (
    deduplicate_raw_records,
    transform_transactions_to_monthly_premiums,
)
from batch_pipeline_reference.validator import validate_and_normalise_records
from batch_pipeline_reference.writer import write_output


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the command-line argument parser.

    The parser defines the required input and output paths used to run
    the batch job from the command line.
    """
    parser = argparse.ArgumentParser(
        description="Aggregate monthly total premiums per partner from raw transaction data."
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the input JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the output CSV file.",
    )
    return parser


def run_batch_job(input_path: Path, output_path: Path) -> None:
    """
    Run the end-to-end premium batch pipeline.

    This function reads the raw input file, validates and normalizes the
    records, applies the business transformation, and writes the final
    aggregated CSV output.

    Parameters
    ----------
    input_path : Path
        Path to the input JSON file containing raw transaction records.
    output_path : Path
        Path where the aggregated CSV output should be written.
    """
    payload: list[dict[str, Any]] = read_transactions(input_path)
    deduplicated_payload, duplicate_count = deduplicate_raw_records(
        payload
    )  # easy to miss via python. SQL offers natively: "insert ... on conflict (payload_hash) do nothing". See: AF pipeline.  pylint: disable=line-too-long
    logger.info("Dropped %d duplicate raw records", duplicate_count)

    validation_result: ValidationResult = validate_and_normalise_records(
        deduplicated_payload
    )

    logger.info("Validation summary: %s", validation_result.summary)

    if validation_result.invalid_records:
        logger.warning(
            "Detected %d invalid records during validation",
            validation_result.summary.invalid_records,
        )

        sample_invalid = validation_result.invalid_records[:5]

        for index, invalid in enumerate(sample_invalid, start=1):
            logger.debug(
                "Invalid record sample %d | error=%s | transaction_id=%s",
                index,
                invalid.error,
                invalid.record.get("transaction_id"),
            )

    logger.info(
        "Proceeding with %d validated transactions",
        validation_result.summary.valid_records,
    )

    aggregated_rows: list[MonthlyPremium] = transform_transactions_to_monthly_premiums(
        records=validation_result.valid_records,
        status=TransactionStatus.PROCESSED,
        fail_on_multiple_currencies=False,
    )
    logger.info("Computed %d aggregated output rows.", len(aggregated_rows))

    write_output(aggregated_rows, output_path)


def main() -> int:
    """
    Execute the batch job from the command line.

    This function parses CLI arguments, invokes the batch pipeline, and
    returns a process exit code compatible with command-line execution.

    Returns
    -------
    int
        Zero when execution completes successfully.
    """
    args: argparse.Namespace = build_parser().parse_args()
    run_batch_job(
        input_path=args.input,
        output_path=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # pragma: no cover
