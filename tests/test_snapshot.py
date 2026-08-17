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


def _book() -> MaturityBook:
    return MaturityBook(
        [
            _tranche("term10", "100.00", 10),
            _tranche("locked20", "200.000", 20, liquidity_class="LOCKED"),
            _tranche("callable30", "50.0", 30, liquidity_class="CALLABLE"),
            _tranche("kzt20", "50000", 20, currency="KZT"),
        ]
    )


def test_snapshot_is_single_currency_duration_explicit_and_additive() -> None:
    snapshot = export_maturity_snapshot(
        _book(),
        as_of=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
        as_of_week=0,
        currency="USDT",
        horizon_weeks=30,
    )

    assert snapshot["schema"] == "maturity.snapshot/v1"
    assert snapshot["currency"] == "USDT"
    assert snapshot["total_open_principal"] == "350"
    assert snapshot["immediately_callable_principal"] == "50"

    assert snapshot["buckets"][9] == {
        "week": 10,
        "scheduled_unlock": "100",
        "cumulative_unlock": "100",
        "scheduled_noncallable_unlock": "100",
        "cumulative_noncallable_unlock": "100",
        "duration_eligible_principal": "200",
    }
    assert snapshot["buckets"][19] == {
        "week": 20,
        "scheduled_unlock": "200",
        "cumulative_unlock": "300",
        "scheduled_noncallable_unlock": "200",
        "cumulative_noncallable_unlock": "300",
        "duration_eligible_principal": "0",
    }
    assert snapshot["buckets"][29] == {
        "week": 30,
        "scheduled_unlock": "50",
        "cumulative_unlock": "350",
        "scheduled_noncallable_unlock": "0",
        "cumulative_noncallable_unlock": "300",
        "duration_eligible_principal": "0",
    }

    assert snapshot["metadata"] == {
        "horizon_weeks": 30,
        "liquidity_outflow_rule": (
            "immediately_callable_principal + cumulative_noncallable_unlock"
        ),
    }
    assert len(snapshot["digest"]) == 64


def test_callable_principal_is_never_counted_twice_in_future_outflow_schedule() -> None:
    snapshot = export_maturity_snapshot(
        _book(),
        as_of=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
        as_of_week=0,
        currency="USDT",
        horizon_weeks=30,
    )

    week_30 = snapshot["buckets"][29]
    contractual_total = Decimal(week_30["cumulative_unlock"])
    noncallable_total = Decimal(week_30["cumulative_noncallable_unlock"])
    callable_now = Decimal(snapshot["immediately_callable_principal"])

    assert contractual_total == Decimal("350")
    assert noncallable_total == Decimal("300")
    assert callable_now + noncallable_total == Decimal("350")
    assert callable_now + contractual_total == Decimal("400")  # explicitly forbidden LCR interpretation


def test_snapshot_decimal_text_is_unique_and_normalized() -> None:
    snapshot = export_maturity_snapshot(
        _book(),
        as_of=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
        as_of_week=0,
        currency="USDT",
        horizon_weeks=30,
    )
    assert snapshot["total_open_principal"] == "350"
    assert snapshot["buckets"][9]["scheduled_unlock"] == "100"
    assert snapshot["buckets"][29]["scheduled_noncallable_unlock"] == "0"


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


@pytest.mark.parametrize("bad_week", [True, 9_007_199_254_740_992])
def test_snapshot_rejects_noncanonical_as_of_week(bad_week) -> None:
    with pytest.raises(MaturityInvariantError, match="safe integer"):
        export_maturity_snapshot(
            MaturityBook([_tranche("a", "100", 12)]),
            as_of=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
            as_of_week=bad_week,
            currency="USDT",
            horizon_weeks=12,
        )
