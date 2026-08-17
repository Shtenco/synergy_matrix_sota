from datetime import UTC, datetime
from decimal import Decimal

import pytest

from sinergy_matrix_sota import (
    MaturityBook,
    MaturityInvariantError,
    Tranche,
    export_maturity_snapshot,
)


def _tranche(
    tid: str,
    principal: str,
    maturity: int,
    *,
    currency: str = "USDT",
    liquidity_class: str = "TERM",
) -> Tranche:
    return Tranche(
        tranche_id=tid,
        owner_ref=f"owner-{tid}",
        principal=Decimal(principal),
        denomination=currency,
        opened_week=0,
        maturity_week=maturity,
        liquidity_class=liquidity_class,
    )


def test_snapshot_is_single_currency_and_duration_explicit() -> None:
    book = MaturityBook(
        [
            _tranche("term10", "100", 10),
            _tranche("locked20", "200", 20, liquidity_class="LOCKED"),
            _tranche("callable30", "50", 30, liquidity_class="CALLABLE"),
            _tranche("kzt20", "50000", 20, currency="KZT"),
        ]
    )
    snapshot = export_maturity_snapshot(
        book,
        as_of=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
        as_of_week=0,
        currency="USDT",
        horizon_weeks=20,
    )

    assert snapshot["schema"] == "maturity.snapshot/v1"
    assert snapshot["currency"] == "USDT"
    assert snapshot["total_open_principal"] == "350"
    assert snapshot["immediately_callable_principal"] == "50"
    assert snapshot["buckets"][9] == {
        "week": 10,
        "scheduled_unlock": "100",
        "cumulative_unlock": "100",
        "duration_eligible_principal": "200",
    }
    assert snapshot["buckets"][19] == {
        "week": 20,
        "scheduled_unlock": "200",
        "cumulative_unlock": "300",
        "duration_eligible_principal": "0",
    }
    assert len(snapshot["digest"]) == 64


def test_snapshot_digest_is_deterministic() -> None:
    book = MaturityBook([_tranche("a", "100", 12)])
    kwargs = {
        "as_of": datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
        "as_of_week": 0,
        "currency": "USDT",
        "horizon_weeks": 12,
    }
    first = export_maturity_snapshot(book, **kwargs)
    second = export_maturity_snapshot(book, **kwargs)
    assert first == second


def test_snapshot_rejects_naive_time() -> None:
    with pytest.raises(MaturityInvariantError):
        export_maturity_snapshot(
            MaturityBook([_tranche("a", "100", 12)]),
            as_of=datetime(2026, 8, 17, 12, 0),
            as_of_week=0,
            currency="USDT",
            horizon_weeks=12,
        )
