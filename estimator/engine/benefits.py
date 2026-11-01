"""UK tax tags and Swiss AHV treatment of each assignment benefit (subtask 10).

UK rule IDs: UK-BEN-01 to 10, DUR-01. Swiss rule IDs: CH-AHV-03 to 07.

Each benefit becomes one line per UK tax year with:
- its cost to the employer in GBP,
- its UK tag: taxable cash, taxable benefit in kind, or not taxable (and why),
- the amounts that are UK taxable cash or benefit in kind,
- the amounts that count as Swiss AHV wage, as cash (grossed up) or in kind (not grossed up).
Qualifying relocation costs share one £8,000 exemption, used in input order (UK-BEN-03).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .duration import Decisions, Segment
from .inputs import (HOUSING, MONTHLY, MOVING_COSTS, OTHER_CASH, OTHER_IN_KIND,
                     RELOCATION_ALLOWANCE, TEMPORARY_HOUSING, Benefit, Case)
from .money import ZERO, pence
from .rules import RuleSet, load_rules

TAXABLE_CASH = "Taxable cash"
TAXABLE_BIK = "Taxable benefit in kind"


@dataclass(frozen=True)
class BenefitLine:
    label: str
    category: str
    cost: Decimal              # GBP the employer pays in this tax year
    uk_tag: str
    uk_cash: Decimal           # UK taxable as cash pay (PAYE and Class 1)
    uk_in_kind: Decimal        # UK taxable as a benefit in kind (Class 1A)
    ahv_cash: Decimal          # AHV wage paid in cash: grossed up when the employer bears contributions
    ahv_in_kind: Decimal       # AHV wage in kind: not grossed up
    rule_ids: tuple[str, ...]

    @property
    def uk_taxable(self) -> Decimal:
        return self.uk_cash + self.uk_in_kind


def amount_in_segment(case: Case, benefit: Benefit, seg: Segment) -> Decimal:
    gbp = case.to_gbp(benefit.amount, benefit.currency)
    if benefit.timing == MONTHLY:
        return gbp * seg.months
    return gbp if seg.is_first else ZERO


def classify(case: Case, seg: Segment, decisions: Decisions,
             rules: RuleSet | None = None) -> list[BenefitLine]:
    r = rules or load_rules()
    exempt_left = r["UK-BEN-03"]["exempt_limit"] if seg.is_first else ZERO
    relief = decisions.relief
    lines = []
    for b in case.benefits:
        cost = amount_in_segment(case, b, seg)
        uk_cash = uk_kind = ahv_cash = ahv_kind = ZERO
        ids: tuple[str, ...]

        if b.category == HOUSING:
            if relief:
                tag, ids = "Not taxable: temporary-workplace relief", ("DUR-01", "UK-BEN-02", "UK-BEN-08")
            else:
                tag, ids, uk_kind = TAXABLE_BIK, ("UK-BEN-01",), cost
            ahv_kind, ahv_ids = _ahv_housing(case, b, seg, r)
            ids += ahv_ids

        elif b.category == TEMPORARY_HOUSING:
            if relief:
                tag, ids = "Not taxable: temporary-workplace relief", ("DUR-01", "UK-BEN-02", "UK-BEN-08")
            else:
                exempt = min(cost, exempt_left)
                exempt_left -= exempt
                tag, uk_kind = _relocation_tag(exempt, cost - exempt), cost - exempt
                ids = ("UK-BEN-03", "UK-BEN-04", "UK-BEN-06")
            ahv_kind, ahv_ids = _ahv_housing(case, b, seg, r)
            ids += ahv_ids

        elif b.category == MOVING_COSTS:
            exempt = min(cost, exempt_left)
            exempt_left -= exempt
            tag, uk_kind = _relocation_tag(exempt, cost - exempt), cost - exempt
            ids = ("UK-BEN-03", "UK-BEN-06", "CH-AHV-05")

        elif b.category == RELOCATION_ALLOWANCE:
            tag, uk_cash, ahv_cash = TAXABLE_CASH, cost, cost
            ids = ("UK-BEN-05", "CH-AHV-06")

        elif b.category == OTHER_CASH:
            tag, uk_cash, ahv_cash = TAXABLE_CASH, cost, cost
            ids = ("UK-BEN-09", "CH-AHV-07")

        elif b.category == OTHER_IN_KIND:
            tag, uk_kind, ahv_kind = TAXABLE_BIK, cost, cost
            ids = ("UK-BEN-10", "CH-AHV-03")

        else:  # Benefit.check() rejects unknown categories; kept for safety
            raise ValueError(f"Unknown benefit category {b.category}")

        lines.append(BenefitLine(b.label, b.category, cost, tag, uk_cash, uk_kind,
                                 ahv_cash, ahv_kind, ids))
    return lines


def _relocation_tag(exempt: Decimal, taxable: Decimal) -> str:
    if taxable == 0:
        return "Not taxable: relocation exemption"
    if exempt == 0:
        return TAXABLE_BIK
    return f"£{pence(exempt):,} not taxable (relocation exemption), £{pence(taxable):,} {TAXABLE_BIK.lower()}"


def _ahv_housing(case: Case, b: Benefit, seg: Segment, r: RuleSet) -> tuple[Decimal, tuple[str, ...]]:
    """Housing is AHV wage in kind, except while a Swiss home is kept (first 12 months)."""
    gbp = case.to_gbp(b.amount, b.currency)
    limit = int(r["CH-AHV-04"]["max_months"])
    if b.timing == MONTHLY:
        counted = seg.months
        if case.swiss_home_kept:
            counted -= max(0, min(seg.months, limit - seg.months_before))
        amount = gbp * counted
    else:  # paid in the first month of the stay
        amount = gbp if seg.is_first and not case.swiss_home_kept else ZERO
    ids = ("CH-AHV-03", "CH-AHV-04") if case.swiss_home_kept else ("CH-AHV-03",)
    return amount, ids
