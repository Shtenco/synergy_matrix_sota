from decimal import Decimal

import pytest

from sinergy_matrix_sota import (
    MaturityBook,
    MaturityInvariantError,
    Tranche,
    ensure_credit_duration,
)


def tranche(tid: str, owner: str, principal: str, opened: int, maturity: int) -> Tranche:
    return Tranche(
        tranche_id=tid,
        owner_ref=owner,
        principal=Decimal(principal),
        denomination="USDT",
        opened_week=opened,
        maturity_week=maturity,
    )


def test_tranche_duration_is_limited_to_reference_1_100_weeks() -> None:
    tranche("a", "u1", "100", 0, 100)
    with pytest.raises(MaturityInvariantError):
        tranche("b", "u1", "100", 0, 101)


def test_duplicate_tranche_is_rejected() -> None:
    book = MaturityBook()
    book.add(tranche("a", "u1", "100", 0, 20))
    with pytest.raises(MaturityInvariantError):
        book.add(tranche("a", "u2", "100", 0, 30))


def test_scheduled_unlocks_are_grouped_by_remaining_duration() -> None:
    book = MaturityBook([
        tranche("a", "u1", "100", 0, 10),
        tranche("b", "u2", "50", 0, 20),
    ])
    unlocks = book.scheduled_unlocks(as_of_week=5, horizon_weeks=20)
    assert unlocks[5] == Decimal("100")
    assert unlocks[15] == Decimal("50")


def test_eligible_funding_requires_strictly_longer_duration() -> None:
    book = MaturityBook([
        tranche("a", "u1", "100", 0, 10),
        tranche("b", "u2", "200", 0, 20),
    ])
    assert book.eligible_funding(as_of_week=0, loan_maturity_weeks=10) == Decimal("200")


def test_borrower_owned_tranche_is_excluded_by_default() -> None:
    book = MaturityBook([
        tranche("borrower", "u1", "100", 0, 30),
        tranche("other", "u2", "250", 0, 30),
    ])
    assert book.eligible_funding(
        as_of_week=0,
        loan_maturity_weeks=12,
        borrower_ref="u1",
    ) == Decimal("250")


def test_owner_exclusion_can_be_disabled_for_explicit_non_credit_analytics() -> None:
    book = MaturityBook([
        tranche("borrower", "u1", "100", 0, 30),
        tranche("other", "u2", "250", 0, 30),
    ])
    assert book.eligible_funding(
        as_of_week=0,
        loan_maturity_weeks=12,
        borrower_ref="u1",
        exclude_borrower_owned_tranches=False,
    ) == Decimal("350")


def test_credit_duration_rule_is_strict() -> None:
    ensure_credit_duration(9, 10)
    with pytest.raises(MaturityInvariantError):
        ensure_credit_duration(10, 10)
