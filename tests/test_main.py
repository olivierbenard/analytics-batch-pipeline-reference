import argparse
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from batch_pipeline_reference import main as main_module


def test_main_calls_run_batch_job_with_parsed_args(monkeypatch: pytest.MonkeyPatch):
    """
    Use:
    - monkeypatch to replace the `run_batch_job` method with a
    mocked implementation.
    - MagicMock to create an object and track its usage.
    """

    # instantiate a simple object that stores custom attributes
    fake_args = argparse.Namespace(
        input=Path("./input/premium_transactions_data_20250306.json"),
        output=Path("./output/output.csv"),
    )

    mock_build_parser = MagicMock()
    mock_build_parser.parse_args.return_value = fake_args

    mock_run_batch_job = MagicMock()

    monkeypatch.setattr(main_module, "build_parser", lambda: mock_build_parser)
    monkeypatch.setattr(main_module, "run_batch_job", mock_run_batch_job)

    result = main_module.main()
    assert result == 0
    mock_run_batch_job.assert_called_once_with(
        input_path=Path("./input/premium_transactions_data_20250306.json"),
        output_path=Path("./output/output.csv"),
    )
