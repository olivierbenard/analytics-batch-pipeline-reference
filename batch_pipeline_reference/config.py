"""
Configuration constants for the premium batch job.

This module centralizes reusable settings such as file encoding,
CSV headers, and other project-wide constants used across the pipeline.
"""

ENCODING: str = "utf-8"
CSV_HEADER: list[str] = ["partner", "month", "currency", "total_premium"]
