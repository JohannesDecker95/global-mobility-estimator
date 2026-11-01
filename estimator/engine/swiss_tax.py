"""Hypothetical Swiss income tax: federal, canton of Zurich and city of Zurich, 2026 (subtask 8).

Rule IDs: CH-TAX-01 to 08. Single person, no children, no church tax, no BVG.
The Personalsteuer (CH-TAX-08) is a head tax, shown separately and left out.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .money import ZERO, positive, round_down
from .rules import RuleSet, load_rules
from .swiss_social import employee_contributions

HYPO_TAX_RULES = ("CH-TAX-01", "CH-TAX-02", "CH-TAX-03", "CH-TAX-04", "CH-TAX-05",
                  "CH-TAX-06", "CH-TAX-07", "CH-SS-01", "CH-SS-02")


def federal_tax(taxable: Decimal, rules: RuleSet | None = None) -> Decimal:
    """CH-TAX-01, CH-TAX-03: federal tax for a single person."""
    r = rules or load_rules()
    tariff, rounding = r["CH-TAX-01"].value, r["CH-TAX-03"].value
    t = round_down(positive(taxable), rounding["income_step"])
    if t >= tariff["flat_rate_from"]:
        tax = t * tariff["flat_rate"]
    else:
        threshold, at, per100 = [b for b in tariff["brackets"] if b[0] <= t][-1]
        tax = at + (t - threshold) / 100 * per100
    tax = round_down(tax, rounding["tax_step"])
    return ZERO if tax < rounding["minimum_tax"] else tax


def zurich_basic_tax(taxable: Decimal, rules: RuleSet | None = None) -> Decimal:
    """CH-TAX-04: the einfache Staatssteuer from the Grundtarif (before the multipliers)."""
    tariff = (rules or load_rules())["CH-TAX-04"].value
    rest = round_down(positive(taxable), tariff["income_step"])
    tax = ZERO
    for width, rate in tariff["brackets"]:
        part = min(rest, width)
        tax += part * rate
        rest -= part
    return tax + positive(rest) * tariff["top_rate"]


@dataclass(frozen=True)
class HypotheticalTax:
    gross: Decimal
    social_security: Decimal
    net_salary: Decimal
    federal_taxable: Decimal
    zurich_taxable: Decimal
    federal: Decimal
    basic: Decimal
    cantonal: Decimal
    communal: Decimal

    @property
    def total(self) -> Decimal:
        return self.federal + self.cantonal + self.communal


def _professional_costs(net_salary: Decimal, deduction: dict) -> Decimal:
    flat = net_salary * deduction["professional_rate"]
    return min(max(flat, deduction["professional_min"]), deduction["professional_max"])


def hypothetical_tax(gross_chf: Decimal, pillar2: bool = True, rules: RuleSet | None = None) -> HypotheticalTax:
    """The annual tax a single person in the city of Zurich would pay on salary and bonus.

    Net salary = gross less employee AHV/IV/EO and ALV (CH-SS-01, 02); then flat
    professional costs and the insurance allowance (CH-TAX-02 federal, CH-TAX-05 Zurich).
    """
    r = rules or load_rules()
    ss = employee_contributions(gross_chf, r)
    net = gross_chf - ss
    fed_ded, zh_ded = r["CH-TAX-02"].value, r["CH-TAX-05"].value
    key = "insurance_single" if pillar2 else "insurance_single_no_pillar2"
    fed_taxable = net - _professional_costs(net, fed_ded) - fed_ded[key]
    zh_taxable = net - _professional_costs(net, zh_ded) - zh_ded[key]
    basic = zurich_basic_tax(zh_taxable, r)
    return HypotheticalTax(
        gross=gross_chf, social_security=ss, net_salary=net,
        federal_taxable=fed_taxable, zurich_taxable=zh_taxable,
        federal=federal_tax(fed_taxable, r), basic=basic,
        cantonal=basic * r["CH-TAX-06"]["multiplier"],
        communal=basic * r["CH-TAX-07"]["multiplier"],
    )
