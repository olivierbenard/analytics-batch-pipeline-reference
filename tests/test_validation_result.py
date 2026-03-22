from __future__ import annotations

from batch_pipeline_reference.models import ValidationResult


def test_has_invalid_records_returns_false_when_invalid_count_is_zero(
    validation_result_valid_only: ValidationResult,
) -> None:
    assert validation_result_valid_only.has_invalid_records() is False
    assert (
        validation_result_valid_only.summary.invalid_records == 0
    )  # this prevents inconsistencies


def test_has_invalid_records_returns_true_when_invalid_count_is_greater_than_zero(
    validation_result_with_invalid: ValidationResult,
) -> None:
    assert validation_result_with_invalid.has_invalid_records() is True
    assert validation_result_with_invalid.summary.invalid_records > 0


def test_validation_result_summary_matches_record_lists(
    validation_result_with_invalid: ValidationResult,
) -> None:
    result = validation_result_with_invalid

    assert result.summary.valid_records == len(result.valid_records)
    assert result.summary.invalid_records == len(result.invalid_records)
    assert result.summary.total_records == (
        len(result.valid_records) + len(result.invalid_records)
    )
