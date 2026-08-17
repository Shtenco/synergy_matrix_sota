"""Reference household-capital and maturity primitives for SINERGY Matrix SOTA."""

from .core import (
    MaturityBook,
    MaturityInvariantError,
    Tranche,
    ensure_credit_duration,
)

__all__ = [
    "MaturityBook",
    "MaturityInvariantError",
    "Tranche",
    "ensure_credit_duration",
]
