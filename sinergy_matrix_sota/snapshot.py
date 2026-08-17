from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from .core import MaturityBook, MaturityInvariantError


ZERO = Decimal("0")
MAX_SAFE_JSON_INTEGER = 9_007_199_254_740_991
LIQUIDITY_OUTFLOW_RULE = (
    "immediately_callable_principal + cumulative_noncallable_unlock"
)


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise MaturityInvariantError("snapshot decimal value must be finite")
    if value == ZERO:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
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

    The snapshot deliberately carries two schedules:

    - `scheduled_unlock/cumulative_unlock`: contractual audit maturity for all
      open tranches, including callable balances at contractual maturity;
    - `scheduled_noncallable_unlock/cumulative_noncallable_unlock`: future
      maturity outflow schedule with CALLABLE balances removed because those
      balances are already represented by `immediately_callable_principal`.

    Financial OS LCR consumes only:

        immediately_callable_principal + cumulative_noncallable_unlock

    The snapshot itself does not calculate LCR because liquid assets and other
    system outflows belong to canonical Financial OS rather than this book.
    """

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise MaturityInvariantError("as_of must be timezone-aware")
    if (
        not isinstance(as_of_week, int)
        or isinstance(as_of_week, bool)
        or as_of_week < 0
        or as_of_week > MAX_SAFE_JSON_INTEGER
    ):
        raise MaturityInvariantError(
            "as_of_week must be a non-negative cross-language safe integer"
        )
    if (
        not isinstance(horizon_weeks, int)
        or isinstance(horizon_weeks, bool)
        or horizon_weeks < 1
        or horizon_weeks > 100
    ):
        raise MaturityInvariantError("horizon_weeks must be integer 1..100")

    denomination = currency.upper().strip()
    if not denomination:
        raise MaturityInvariantError("currency is required")

    total_open = book.total_open_principal(as_of_week, denomination)
    callable_principal = book.immediately_callable_principal(as_of_week, denomination)
    if callable_principal > total_open:
        raise MaturityInvariantError(
            "immediately_callable_principal cannot exceed total_open_principal"
        )

    contractual_unlocks = book.scheduled_unlocks(
        as_of_week,
        horizon_weeks=horizon_weeks,
        denomination=denomination,
    )
    noncallable_unlocks = book.scheduled_noncallable_unlocks(
        as_of_week,
        horizon_weeks=horizon_weeks,
        denomination=denomination,
    )

    cumulative_contractual = ZERO
    cumulative_noncallable = ZERO
    buckets: list[dict[str, Any]] = []
    for week in range(1, horizon_weeks + 1):
        contractual = contractual_unlocks[week]
        noncallable = noncallable_unlocks[week]
        if noncallable > contractual:
            raise MaturityInvariantError(
                "non-callable scheduled unlock cannot exceed contractual scheduled unlock"
            )
        cumulative_contractual += contractual
        cumulative_noncallable += noncallable
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
                "scheduled_unlock": _decimal_text(contractual),
                "cumulative_unlock": _decimal_text(cumulative_contractual),
                "scheduled_noncallable_unlock": _decimal_text(noncallable),
                "cumulative_noncallable_unlock": _decimal_text(cumulative_noncallable),
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
        "metadata": {
            "horizon_weeks": horizon_weeks,
            "liquidity_outflow_rule": LIQUIDITY_OUTFLOW_RULE,
        },
    }
    payload["digest"] = _canonical_digest(payload)
    return payload
