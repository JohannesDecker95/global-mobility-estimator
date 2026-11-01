"""Swiss social security: AHV/IV/EO and unemployment insurance (ALV), 2026 (subtask 9).

Rule IDs: CH-SS-01 (AHV/IV/EO, 5.3% each side, no ceiling) and CH-SS-02 (ALV, 1.1% each
side up to CHF 148,200 a year). Employer and employee rates are equal, so the employer
share on a base is the same amount as the employee share.
"""
from __future__ import annotations

from decimal import Decimal

from .money import positive
from .rules import RuleSet, load_rules

SWISS_SS_RULES = ("CH-SS-01", "CH-SS-02")


def _ceiling(alv, months: int, chf_per_unit: Decimal) -> Decimal:
    """The ALV ceiling for `months` months, in the currency of the base."""
    return alv["ceiling"] * Decimal(months) / 12 / chf_per_unit


def employee_contributions(base: Decimal, rules: RuleSet | None = None, months: int = 12,
                           chf_per_unit: Decimal = Decimal(1)) -> Decimal:
    """Employee AHV/IV/EO + ALV on a base covering `months` months.

    The base may be in CHF (chf_per_unit = 1) or in GBP (chf_per_unit = the exchange rate).
    """
    r = rules or load_rules()
    ahv, alv = r["CH-SS-01"], r["CH-SS-02"]
    ceiling = _ceiling(alv, months, chf_per_unit)
    return ahv["employee_rate"] * positive(base) + alv["employee_rate"] * min(positive(base), ceiling)


def employer_contributions(base: Decimal, rules: RuleSet | None = None, months: int = 12,
                           chf_per_unit: Decimal = Decimal(1)) -> Decimal:
    """Employer AHV/IV/EO + ALV on the same base."""
    r = rules or load_rules()
    ahv, alv = r["CH-SS-01"], r["CH-SS-02"]
    ceiling = _ceiling(alv, months, chf_per_unit)
    return ahv["employer_rate"] * positive(base) + alv["employer_rate"] * min(positive(base), ceiling)
