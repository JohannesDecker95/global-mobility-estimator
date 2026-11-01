"""Duration advice: which length of stay is cheapest per month (spec section 17).

For every length from 12 to 60 months the full estimate is run and the all-in cost
(cost table plus immigration) is divided by the months. The advice reports:
- the planned length,
- the cheapest length per month overall,
- the cheapest length at or above the planned one (when the business needs at least that long),
- what one more month than planned costs, and which rule thresholds it crosses.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from .cost_table import estimate
from .inputs import MAX_MONTHS, MIN_MONTHS, Case, EngineInputError
from .money import pence
from .rules import RuleSet, load_rules


@dataclass(frozen=True)
class Row:
    months: int
    social_security: str
    relief: bool
    employer_cost: Decimal
    immigration: Decimal
    all_in: Decimal
    per_month: Decimal


@dataclass(frozen=True)
class Advice:
    rows: list[Row]
    planned: Row
    cheapest: Row
    cheapest_from_planned: Row
    next_month: Row | None
    next_month_extra: Decimal | None
    thresholds_crossed: list[str]


def scan(case: Case, lo: int = MIN_MONTHS, hi: int = MAX_MONTHS, rules: RuleSet | None = None) -> list[Row]:
    r = rules or load_rules()
    if not MIN_MONTHS <= lo <= hi <= MAX_MONTHS:
        raise EngineInputError(f"The advice range must lie within {MIN_MONTHS} to {MAX_MONTHS} months.")
    rows = []
    for m in range(lo, hi + 1):
        e = estimate(replace(case, months=m), r)
        rows.append(Row(m, e.decisions.social_security.system, e.decisions.relief,
                        e.total, e.immigration_total, e.all_in, e.per_month))
    return rows


def _cheapest(rows: list[Row]) -> Row:
    # ties go to the longer stay: same cost per month, more work done
    return min(rows, key=lambda row: (pence(row.per_month), -row.months))


def advise(case: Case, lo: int = MIN_MONTHS, hi: int = MAX_MONTHS, rules: RuleSet | None = None) -> Advice:
    r = rules or load_rules()
    lo, hi = min(lo, case.months), max(hi, case.months)
    rows = scan(case, lo, hi, r)
    by_months = {row.months: row for row in rows}
    planned = by_months[case.months]
    nxt = by_months.get(case.months + 1)
    crossed = []
    if nxt:
        if planned.relief and not nxt.relief:
            crossed.append("temporary-workplace relief ends for the whole stay (DUR-01)")
        if planned.social_security != nxt.social_security:
            crossed.append("UK National Insurance replaces Swiss social security (DUR-02, DUR-03)")
    return Advice(
        rows=rows, planned=planned, cheapest=_cheapest(rows),
        cheapest_from_planned=_cheapest([row for row in rows if row.months >= case.months]),
        next_month=nxt, next_month_extra=(nxt.all_in - planned.all_in) if nxt else None,
        thresholds_crossed=crossed,
    )
