"""
Custom helpers.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from batch_pipeline_reference.config import ENCODING


def compute_payload_hash(record: dict[str, Any]) -> str:
    """
    Compute a deterministic SHA-256 hash for a raw JSON record.
    """
    canonical_json = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode(ENCODING)).hexdigest()
