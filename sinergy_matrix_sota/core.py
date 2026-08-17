from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable


ZERO = Decimal("0")
ELIGIBLE_TERM_CLASSES = frozenset({"TERM", "LOCKED"})
VALID_LIQUIDITY_CLASSES = frozenset({"CALLABLE", "TERM", "LOCKED", "RESTRICTED"})
VALID_STATUSES = frozenset({"OPEN", "MATURED", "WITHDRAWN", "ROLLED", "RESTRICTED"})


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
        denomination = self.denomination.upper().strip()
        liquidity_class = self.liquidity_class.upper().strip()
        status = self.status.upper().strip()

        if not self.tranche_id:
            raise MaturityInvariantError("tranche_id is required")
        if not self.owner_ref:
            raise MaturityInvariantError("owner_ref is required")
        if principal <= ZERO:
            raise MaturityInvariantError("principal must be positive")
        if not denomination:
            raise MaturityInvariantError("denomination is required")
        if liquidity_class not in VALID_LIQUIDITY_CLASSES:
            raise MaturityInvariantError(f"invalid liquidity_class: {liquidity_class}")
        if status not in VALID_STATUSES:
            raise MaturityInvariantError(f"invalid status: {status}")
        if self.opened_week < 0:
            raise MaturityInvariantError("opened_week must be non-negative")

        duration = self.maturity_week - self.opened_week
        if duration < 1 or duration > 100:
            raise MaturityInvariantError("reference tranche duration must be 1..100 weeks")

        object.__setattr__(self, "principal", principal)
        object.__setattr__(self, "denomination", denomination)
        object.__setattr__(self, "liquidity_class", liquidity_class)
        object.__setattr__(self, "status", status)

    def remaining_weeks(self, as_of_week: int) -> int:
        return max(0, self.maturity_week - as_of_week)

    def is_open_at(self, as_of_week: int) -> bool:
        return self.status == "OPEN" and self.opened_week <= as_of_week < self.maturity_week


@dataclass
class MaturityBook:
    """Independent-tranche funding book.

    The book calculates duration availability only. It does not decide borrower
    creditworthiness, yield, money issuance or system solvency. Monetary totals
    are never added across denominations without an explicit conversion layer.
    """

    tranches: list[Tranche] = field(default_factory=list)

    def add(self, tranche: Tranche) -> None:
        if any(existing.tranche_id == tranche.tranche_id for existing in self.tranches):
            raise MaturityInvariantError(f"duplicate tranche_id: {tranche.tranche_id}")
        self.tranches.append(tranche)

    def active_denominations(self, as_of_week: int) -> tuple[str, ...]:
        return tuple(
            sorted({t.denomination for t in self.tranches if t.is_open_at(as_of_week)})
        )

    def _resolve_denomination(self, as_of_week: int, denomination: str | None) -> str:
        if denomination is not None:
            normalized = denomination.upper().strip()
            if not normalized:
                raise MaturityInvariantError("denomination must not be empty")
            return normalized

        active = self.active_denominations(as_of_week)
        if len(active) == 1:
            return active[0]
        if not active:
            raise MaturityInvariantError(
                "denomination is required when no active tranche can establish the unit"
            )
        raise MaturityInvariantError(
            "denomination is required when multiple active currencies exist"
        )

    def _open_in_currency(self, as_of_week: int, denomination: str) -> Iterable[Tranche]:
        return (
            tranche
            for tranche in self.tranches
            if tranche.is_open_at(as_of_week) and tranche.denomination == denomination
        )

    def total_open_principal(
        self,
        as_of_week: int,
        denomination: str | None = None,
    ) -> Decimal:
        currency = self._resolve_denomination(as_of_week, denomination)
        return sum(
            (t.principal for t in self._open_in_currency(as_of_week, currency)),
            ZERO,
        )

    def immediately_callable_principal(
        self,
        as_of_week: int,
        denomination: str | None = None,
    ) -> Decimal:
        currency = self._resolve_denomination(as_of_week, denomination)
        return sum(
            (
                t.principal
                for t in self._open_in_currency(as_of_week, currency)
                if t.liquidity_class == "CALLABLE"
            ),
            ZERO,
        )

    def scheduled_unlocks(
        self,
        as_of_week: int,
        horizon_weeks: int = 100,
        denomination: str | None = None,
    ) -> dict[int, Decimal]:
        if horizon_weeks < 1 or horizon_weeks > 100:
            raise MaturityInvariantError("horizon_weeks must be 1..100")
        currency = self._resolve_denomination(as_of_week, denomination)
        result = {week: ZERO for week in range(1, horizon_weeks + 1)}
        for tranche in self._open_in_currency(as_of_week, currency):
            remaining = tranche.remaining_weeks(as_of_week)
            if 1 <= remaining <= horizon_weeks:
                result[remaining] += tranche.principal
        return result

    def eligible_funding(
        self,
        *,
        as_of_week: int,
        loan_maturity_weeks: int,
        denomination: str | None = None,
        borrower_ref: str | None = None,
        exclude_borrower_owned_tranches: bool = True,
        eligible_liquidity_classes: frozenset[str] = ELIGIBLE_TERM_CLASSES,
    ) -> Decimal:
        """Return term principal whose remaining duration strictly exceeds the loan.

        By default, callable/restricted tranches are excluded and tranches owned
        by the borrower are excluded. This prevents demandable money or the
        borrower's own current savings from being presented as independent term
        funding for the same simultaneous credit exposure.
        """

        if loan_maturity_weeks < 1:
            raise MaturityInvariantError("loan_maturity_weeks must be positive")
        currency = self._resolve_denomination(as_of_week, denomination)

        eligible = ZERO
        for tranche in self._open_in_currency(as_of_week, currency):
            if tranche.liquidity_class not in eligible_liquidity_classes:
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
