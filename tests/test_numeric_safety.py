from decimal import Decimal

import pytest

from sinergy_matrix_sota import MaturityInvariantError, Tranche


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity", Decimal("NaN")])
def test_tranche_principal_rejects_non_finite_values(bad) -> None:
    with pytest.raises(MaturityInvariantError):
        Tranche(
            tranche_id="bad-principal",
            owner_ref="owner-1",
            principal=bad,
            denomination="USDT",
            opened_week=0,
            maturity_week=12,
            liquidity_class="TERM",
        )
