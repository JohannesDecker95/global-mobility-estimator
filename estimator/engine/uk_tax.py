"""UK income tax and National Insurance, England and Northern Ireland, 2026/27 (subtask 7).

Rule IDs: UK-IT-01 to 05 (income tax), UK-NI-01 to 03 (National Insurance).
The tax works on a tax year's taxable earnings. For a part tax year (the last year
of a stay that does not end on 5 April) the full allowance and bands apply, as the
employee is assumed UK resident until departure (split-year treatment, spec section 17).
National Insurance works per monthly earnings period, so its thresholds scale with
the months worked in the tax year.
"""
from __future__ import annotations

from decimal import Decimal

from .money import ZERO, positive
from .rules import RuleSet, load_rules

INCOME_TAX_RULES = ("UK-IT-01", "UK-IT-02", "UK-IT-03", "UK-IT-04", "UK-IT-05")


def personal_allowance(income: Decimal, rules: RuleSet | None = None) -> Decimal:
    """UK-IT-01, UK-IT-02: £12,570, cut by £1 for every £2 above £100,000."""
    r = rules or load_rules()
    pa = r["UK-IT-01"]["personal_allowance"]
    taper = r["UK-IT-02"]
    cut = positive(income - taper["taper_from"]) * taper["reduction_per_pound"]
    return positive(pa - cut)


def income_tax(income: Decimal, rules: RuleSet | None = None) -> Decimal:
    """UKTax(X): income tax on total taxable earnings X for one tax year (UK-IT-01 to 05)."""
    r = rules or load_rules()
    taxable = positive(income - personal_allowance(income, r))
    basic, higher, additional = r["UK-IT-03"], r["UK-IT-04"], r["UK-IT-05"]
    basic_part = min(taxable, basic["band_width"])
    higher_part = positive(min(taxable, higher["upper_limit"]) - basic["band_width"])
    additional_part = positive(taxable - higher["upper_limit"])
    return (basic_part * basic["rate"] + higher_part * higher["rate"]
            + additional_part * additional["rate"])


def nic_employee(earnings: Decimal, months: int = 12, rules: RuleSet | None = None) -> Decimal:
    """UK-NI-01: employee Class 1, 8% between the thresholds, 2% above, over `months` monthly periods."""
    r = (rules or load_rules())["UK-NI-01"]
    share = Decimal(months) / 12
    pt, uel = r["primary_threshold"] * share, r["upper_earnings_limit"] * share
    return r["main_rate"] * positive(min(earnings, uel) - pt) + r["upper_rate"] * positive(earnings - uel)


def nic_employer(earnings: Decimal, months: int = 12, rules: RuleSet | None = None) -> Decimal:
    """UK-NI-02: employer Class 1, 15% above the secondary threshold."""
    r = (rules or load_rules())["UK-NI-02"]
    return r["rate"] * positive(earnings - r["secondary_threshold"] * Decimal(months) / 12)


def class_1a(benefits_in_kind: Decimal, rules: RuleSet | None = None) -> Decimal:
    """UK-NI-03: Class 1A, 15% of taxable benefits in kind."""
    return (rules or load_rules())["UK-NI-03"]["rate"] * positive(benefits_in_kind)


def closed_form_gross_up(income: Decimal, rules: RuleSet | None = None) -> Decimal | None:
    """T = (0.45 I - 13,797) / 0.55, valid only when I + T is above £125,140. A test aid only."""
    r = rules or load_rules()
    rate = r["UK-IT-05"]["rate"]
    # Above the additional-rate limit there is no allowance: UKTax(X) = rate X - offset
    offset = rate * r["UK-IT-04"]["upper_limit"] - income_tax(r["UK-IT-04"]["upper_limit"], r)
    t = (rate * income - offset) / (1 - rate)
    return t if income + t > r["UK-IT-04"]["upper_limit"] else None
