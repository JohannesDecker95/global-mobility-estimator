"""Immigration costs by length of stay (spec sections 12 and 17).

Rule IDs: IMM-SP-01 to 03, IMM-WP-03, IMM-WP-04, IMM-BV-01, DUR-04, DUR-05.
Leave = certificate period + 14 days (IMM-WP-02), which decides the visa fee band and
the health surcharge. The requirement texts for tab 2 are in requirements.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from .inputs import Case
from .money import ZERO
from .rules import RuleSet, load_rules


@dataclass(frozen=True)
class CostItem:
    label: str
    amount: Decimal
    paid_by: str
    rule_ids: tuple[str, ...]
    key: str = ""             # links the cost to its requirement (requirements_2026.json)


def costs(case: Case, rules: RuleSet | None = None) -> list[CostItem]:
    r = rules or load_rules()
    m = case.months
    licence = r["IMM-SP-01"]
    isc, fee_band, ihs = r["IMM-SP-03"], r["DUR-04"], r["DUR-05"]
    size = "large" if case.sponsor_large else "small"

    licence_fee = ZERO if case.sponsor_licence_held else licence[f"fee_{size}"]
    first, per6 = isc[f"{size}_first_12_months"], isc[f"{size}_per_6_months"]
    periods = (Decimal(m - 12) / int(ihs["isc_period_months"])).to_integral_value(ROUND_CEILING) if m > 12 else 0
    skills_charge = first + per6 * periods

    visa_fee = fee_band["fee_up_to"] if m < int(fee_band["up_to_months"]) else fee_band["fee_over"]
    years, rest = divmod(m, 12)
    half_up_to = int(ihs["ihs_half_year_up_to_months"])
    # the 14 extra days make even a whole number of years end with a short part year
    part = Decimal("0.5") if rest < half_up_to else Decimal(1)
    surcharge = r["IMM-WP-04"]["per_year"] * (years + part)

    return [
        CostItem("Sponsor licence" + (" (already held)" if case.sponsor_licence_held else ""),
                 licence_fee, "sponsor", ("IMM-SP-01",), "sponsor_licence"),
        CostItem("Certificate of sponsorship", r["IMM-SP-02"]["fee"], "sponsor", ("IMM-SP-02",), "certificate"),
        CostItem(f"Immigration Skills Charge, {m} months", skills_charge, "sponsor", ("IMM-SP-03", "DUR-05"),
                 "skills_charge"),
        CostItem("Visa application from outside the UK", visa_fee, "employee", ("IMM-WP-03", "DUR-04"), "visa_fee"),
        CostItem(f"Immigration Health Surcharge, {years + part} years", surcharge, "employee",
                 ("IMM-WP-04", "DUR-05"), "health_surcharge"),
        CostItem("ETA for a business visit before the move", r["IMM-BV-01"]["fee"], "employee", ("IMM-BV-01",), "eta"),
    ]


def total(case: Case, rules: RuleSet | None = None) -> Decimal:
    return sum((c.amount for c in costs(case, rules)), ZERO)
