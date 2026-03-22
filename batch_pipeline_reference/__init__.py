"""
Batch Pipeline Reference package.

This package contains a reference Python implementation for validating,
transforming, and aggregating premium transaction data into a monthly
reporting output.
"""

from batch_pipeline_reference.logger import get_configured_logger

logger = get_configured_logger(log_level="DEBUG")
