from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


ZERO = Decimal("0")


class MaturityInvariantError(ValueError):
    """Raised when a household-funding duration invariant is violated."""


def _d(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def ensure_credit_duration(loan_maturity_weeks: int, funding_remaining_weeks: int) -> None:
    """Reference SINERGY rule: credit must end before its funding tranche."""

    if loan_maturity_weeks < 1 or funding_remaining_weeks < 1:
        raise MaturityInvariantError("maturities must be positive")
    if loan_maturity_weeks >= funding_remaining_weeks:
        raise MaturityInvariantError(
            "loan maturity must be strictly shorter than funding remaining maturity"
        )


@dataclass(frozen=True)
class Tranche:
    tranche_id: str
    owner_ref: str
    principal: Decimal
    denomination: str
    opened_week: int
    maturity_week: int
    liquidity_class: str = "TERM"
    status: str = "OPEN"

    def __post_init__(self) -> None:
        principal = _d(self.principal)
        if not self.tranche_id:
            raise MaturityInvariantError("tranche_id is required")
        if not self.owner_ref:
            raise MaturityInvariantError("owner_ref is required")
        if principal <= ZERO:
            raise MaturityInvariantError("principal must be positive")
        if self.opened_week < 0:
            raise MaturityInvariantError("opened_week must be non-negative")
        duration = self.maturity_week - self.opened_week
        if duration < 1 or duration > 100:
            raise MaturityInvariantError("reference tranche duration must be 1..100 weeks")
        object.__setattr__(self, "principal", principal)

    def remaining_weeks(self, as_of_week: int) -> int:
        return max(0, self.maturity_week - as_of_week)

    def is_open_at(self, as_of_week: int) -> bool:
        return self.status == "OPEN" and self.opened_week <= as_of_week < self.maturity_week


@dataclass
class MaturityBook:
    """Independent-tranche funding book.

    The book calculates duration availability only. It does not decide borrower
    creditworthiness, yield, money issuance or system solvency.
    """

    tranches: list[Tranche] = field(default_factory=list)

    def add(self, tranche: Tranche) -> None:
        if any(existing.tranche_id == tranche.tranche_id for existing in self.tranches):
            raise MaturityInvariantError(f"duplicate tranche_id: {tranche.tranche_id}")
        self.tranches.append(tranche)

    def total_open_principal(self, as_of_week: int) -> Decimal:
        return sum(
            (t.principal for t in self.tranches if t.is_open_at(as_of_week)),
            ZERO,
        )

    def scheduled_unlocks(self, as_of_week: int, horizon_weeks: int = 100) -> dict[int, Decimal]:
        if horizon_weeks < 1 or horizon_weeks > 100:
            raise MaturityInvariantError("horizon_weeks must be 1..100")
        result = {week: ZERO for week in range(1, horizon_weeks + 1)}
        for tranche in self.tranches:
            if not tranche.is_open_at(as_of_week):
                continue
            remaining = tranche.remaining_weeks(as_of_week)
            if 1 <= remaining <= horizon_weeks:
                result[remaining] += tranche.principal
        return result

    def eligible_funding(
        self,
        *,
        as_of_week: int,
        loan_maturity_weeks: int,
        borrower_ref: str | None = None,
        exclude_borrower_owned_tranches: bool = True,
    ) -> Decimal:
        """Return principal whose remaining duration strictly exceeds the loan.

        By default, tranches owned by the borrower are excluded. This encodes
        the historical non-circularity rule that a participant's own current
        savings should not be presented as independent funding for the same
        participant's simultaneous credit exposure.
        """

        if loan_maturity_weeks < 1:
            raise MaturityInvariantError("loan_maturity_weeks must be positive")

        eligible = ZERO
        for tranche in self.tranches:
            if not tranche.is_open_at(as_of_week):
                continue
            if (
                exclude_borrower_owned_tranches
                and borrower_ref is not None
                and tranche.owner_ref == borrower_ref
            ):
                continue
            if tranche.remaining_weeks(as_of_week) > loan_maturity_weeks:
                eligible += tranche.principal
        return eligible
