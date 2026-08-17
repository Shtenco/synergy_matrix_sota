import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sinergy_matrix_sota import MaturityBook, Tranche, export_maturity_snapshot


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/conformance/maturity_snapshot_v1_callable_term_locked.json"


def _tranche(
    tranche_id: str,
    principal: str,
    maturity_week: int,
    liquidity_class: str,
) -> Tranche:
    return Tranche(
        tranche_id=tranche_id,
        owner_ref=f"owner-{tranche_id}",
        principal=Decimal(principal),
        denomination="USD",
        opened_week=0,
        maturity_week=maturity_week,
        liquidity_class=liquidity_class,
    )


def test_matrix_producer_reproduces_shared_maturity_fixture_exactly() -> None:
    book = MaturityBook(
        [
            _tranche("callable-4", "100.000", 4, "CALLABLE"),
            _tranche("term-4", "200.00", 4, "TERM"),
            _tranche("locked-8", "300.0", 8, "LOCKED"),
        ]
    )
    actual = export_maturity_snapshot(
        book,
        as_of=datetime(2026, 8, 17, 12, 0, tzinfo=UTC),
        as_of_week=0,
        currency="usd",
        horizon_weeks=8,
    )
    expected = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert actual == expected
    assert actual["digest"] == "05a7f12a360529058864357d0a4f526f5c7c7ed02e6fa63ff3e5447b64358416"


def test_fixture_exposes_contractual_and_lcr_outflow_views_separately() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    week4 = fixture["buckets"][3]
    week8 = fixture["buckets"][7]

    assert week4["cumulative_unlock"] == "300"
    assert week4["cumulative_noncallable_unlock"] == "200"
    assert Decimal(fixture["immediately_callable_principal"]) + Decimal(
        week4["cumulative_noncallable_unlock"]
    ) == Decimal("300")

    assert week8["cumulative_unlock"] == "600"
    assert week8["cumulative_noncallable_unlock"] == "500"
    assert Decimal(fixture["immediately_callable_principal"]) + Decimal(
        week8["cumulative_noncallable_unlock"]
    ) == Decimal("600")
