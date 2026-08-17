"""Reference household-capital and maturity primitives for SINERGY Matrix SOTA."""

from .core import (
    MaturityBook,
    MaturityInvariantError,
    Tranche,
    ensure_credit_duration,
)
from .snapshot import export_maturity_snapshot

__all__ = [
    "MaturityBook",
    "MaturityInvariantError",
    "Tranche",
    "ensure_credit_duration",
    "export_maturity_snapshot",
]
