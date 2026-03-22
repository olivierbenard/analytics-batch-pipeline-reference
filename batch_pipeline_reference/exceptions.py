"""
Custom exception types used by the premium batch job.

These exceptions make validation, transformation, and pipeline failures
more explicit and easier to reason about across the codebase.
"""


class BatchJobError(Exception):
    """
    Base exception for the batch job.
    """


class InvalidRecordError(BatchJobError):
    """
    Raised when an input record is invalid.
    """


class MixedCurrencyError(BatchJobError):
    """
    Raised when successful transactions contain more than one currency.
    """
