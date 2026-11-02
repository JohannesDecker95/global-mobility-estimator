"""Engine inputs: one assignment case and its benefits.

The API layer (forms/serializers) turns the request into a Case and gives readable
messages for bad input. The engine checks the same limits again and raises
EngineInputError, so it is safe to call on its own.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

ZERO = Decimal(0)

MIN_MONTHS, MAX_MONTHS = 12, 60
# The stay starts on the 6th of a month inside UK tax year 2026/27, the year the rules cover:
# 0 = 6 April 2026 ... 11 = 6 March 2027 (decision of 2 November 2026).
MAX_START_OFFSET = 11

# Benefit categories the tool supports (decision of 1 November 2026, spec section 4).
HOUSING = "housing"
TEMPORARY_HOUSING = "temporary_housing"
MOVING_COSTS = "moving_costs"
RELOCATION_ALLOWANCE = "relocation_allowance"
OTHER_CASH = "other_cash_allowance"
OTHER_IN_KIND = "other_benefit_in_kind"
CATEGORIES = (HOUSING, TEMPORARY_HOUSING, MOVING_COSTS, RELOCATION_ALLOWANCE, OTHER_CASH, OTHER_IN_KIND)

MONTHLY = "monthly"      # the amount is paid every month of the stay
ONE_OFF = "one_off"      # the amount is paid once, in the first month
TIMINGS = (MONTHLY, ONE_OFF)

CURRENCIES = ("GBP", "CHF")


class EngineInputError(ValueError):
    """An input the engine cannot calculate with."""


@dataclass(frozen=True)
class Benefit:
    label: str
    category: str
    amount: Decimal
    currency: str = "GBP"
    timing: str = ONE_OFF

    def check(self) -> None:
        if self.category not in CATEGORIES:
            raise EngineInputError(f"Benefit '{self.label}': unknown category '{self.category}'.")
        if self.timing not in TIMINGS:
            raise EngineInputError(f"Benefit '{self.label}': timing must be one of {', '.join(TIMINGS)}.")
        if self.currency not in CURRENCIES:
            raise EngineInputError(f"Benefit '{self.label}': currency must be GBP or CHF.")
        if not isinstance(self.amount, Decimal) or self.amount < 0:
            raise EngineInputError(f"Benefit '{self.label}': amount must be a Decimal of 0 or more.")


@dataclass(frozen=True)
class Case:
    """One assignment from Zurich to London, starting on the 6th of a month in 2026/27."""

    months: int = 24
    start_offset: int = 0                 # months from 6 April 2026 to the start, 0 to 11
    salary_chf: Decimal = Decimal("150000")
    bonus_chf: Decimal = Decimal("20000")
    fx_chf_per_gbp: Decimal = Decimal("1.10")
    benefits: tuple[Benefit, ...] = field(default_factory=tuple)
    months_with_employer: int = 36
    pillar2: bool = True                  # employee pays into pillar 2/3a (insurance allowance)
    continuing_employment: bool = True    # the Swiss contract continues during the posting
    housing_reasonable: bool = True       # flat in line with a suitable hotel (EIM77010)
    swiss_home_kept: bool = False         # WML Rz 3008
    art17_exception: bool = False         # agreed by both authorities
    sponsor_large: bool = True
    sponsor_licence_held: bool = False
    # Interpretation switches (decisions of 1 November 2026). Both False = the literal
    # reading of the candidate pack, shown as a comparison line.
    ahv_full_base: bool = True
    twr_rule: bool = True

    def check(self) -> None:
        if not isinstance(self.months, int) or not MIN_MONTHS <= self.months <= MAX_MONTHS:
            raise EngineInputError(f"The assignment must last {MIN_MONTHS} to {MAX_MONTHS} whole months.")
        if not isinstance(self.start_offset, int) or not 0 <= self.start_offset <= MAX_START_OFFSET:
            raise EngineInputError("The assignment must start between 6 April 2026 and 6 March 2027.")
        for name in ("salary_chf", "bonus_chf"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or value < 0:
                raise EngineInputError(f"{name} must be a Decimal of 0 or more.")
        if not isinstance(self.fx_chf_per_gbp, Decimal) or self.fx_chf_per_gbp <= 0:
            raise EngineInputError("The exchange rate must be a Decimal greater than 0.")
        if self.months_with_employer < 0:
            raise EngineInputError("Months worked for the employer cannot be negative.")
        for benefit in self.benefits:
            benefit.check()

    def to_gbp(self, amount: Decimal, currency: str) -> Decimal:
        return amount / self.fx_chf_per_gbp if currency == "CHF" else amount


def pack_test_case(**changes) -> Case:
    """The candidate pack's test case: Zurich to London, 6 April 2026 to 5 April 2028."""
    benefits = (
        Benefit("Housing in London", HOUSING, Decimal("3000"), "GBP", MONTHLY),
        Benefit("Relocation allowance", RELOCATION_ALLOWANCE, Decimal("5000"), "CHF", ONE_OFF),
        Benefit("Moving costs (flights, shipping)", MOVING_COSTS, Decimal("6000"), "GBP", ONE_OFF),
        Benefit("Temporary housing, first 4 weeks", TEMPORARY_HOUSING, Decimal("4000"), "GBP", ONE_OFF),
    )
    case = Case(benefits=benefits)
    return Case(**{**case.__dict__, **changes})
