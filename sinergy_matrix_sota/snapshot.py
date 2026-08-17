from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from .core import MaturityBook, MaturityInvariantError


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def export_maturity_snapshot(
    book: MaturityBook,
    *,
    as_of: datetime,
    as_of_week: int,
    currency: str,
    horizon_weeks: int = 100,
) -> dict[str, Any]:
    """Export one denomination of the funding book as `maturity.snapshot/v1`.

    The snapshot contains contractual funding-duration state only. It does not
    calculate LCR because liquid assets and other system outflows belong to the
    canonical Financial OS rather than the household maturity book.
    """

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise MaturityInvariantError("as_of must be timezone-aware")
    if as_of_week < 0:
        raise MaturityInvariantError("as_of_week must be non-negative")
    if horizon_weeks < 1 or horizon_weeks > 100:
        raise MaturityInvariantError("horizon_weeks must be 1..100")

    denomination = currency.upper().strip()
    if not denomination:
        raise MaturityInvariantError("currency is required")

    total_open = book.total_open_principal(as_of_week, denomination)
    callable_principal = book.immediately_callable_principal(as_of_week, denomination)
    unlocks = book.scheduled_unlocks(
        as_of_week,
        horizon_weeks=horizon_weeks,
        denomination=denomination,
    )

    cumulative = Decimal("0")
    buckets: list[dict[str, Any]] = []
    for week in range(1, horizon_weeks + 1):
        cumulative += unlocks[week]
        duration_eligible = book.eligible_funding(
            as_of_week=as_of_week,
            loan_maturity_weeks=week,
            denomination=denomination,
            borrower_ref=None,
            exclude_borrower_owned_tranches=False,
        )
        buckets.append(
            {
                "week": week,
                "scheduled_unlock": _decimal_text(unlocks[week]),
                "cumulative_unlock": _decimal_text(cumulative),
                "duration_eligible_principal": _decimal_text(duration_eligible),
            }
        )

    payload: dict[str, Any] = {
        "schema": "maturity.snapshot/v1",
        "as_of": as_of.isoformat(),
        "as_of_week": as_of_week,
        "currency": denomination,
        "total_open_principal": _decimal_text(total_open),
        "immediately_callable_principal": _decimal_text(callable_principal),
        "buckets": buckets,
        "metadata": {"horizon_weeks": horizon_weeks},
    }
    payload["digest"] = _canonical_digest(payload)
    return payload
