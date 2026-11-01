"""The cost table: four sections per UK tax year, totals and the multiple of home pay.

This is where the modules meet (spec sections 10, 11, 16 and 17):

1. Home pay            salary and bonus, as if the employee had stayed in Zurich
2. Assignment benefits each benefit with its UK tag (benefits.py)
3. Host tax and charges UK income tax including tax on tax (gross_up.py), UK National
                       Insurance or Swiss social security (social_security.py)
4. Deductions          hypothetical Swiss income tax and social security (swiss_tax.py)

Rounding policy (spec section 11): compute unrounded, round each line to the penny when
it enters the table, and add the rounded lines, so the printed table always adds up.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal

from . import immigration
from .benefits import classify
from .duration import Decisions, Segment, decide_all, segments
from .gross_up import Trace, solve_swiss, solve_uk
from .inputs import Case
from .money import ZERO, pence
from .rules import RuleSet, load_rules
from .social_security import SWISS
from .swiss_social import employee_contributions, employer_contributions
from .swiss_tax import HYPO_TAX_RULES, HypotheticalTax, hypothetical_tax
from .uk_tax import INCOME_TAX_RULES, class_1a, nic_employer

HOME, BENEFITS, HOST, DEDUCTIONS = "home_pay", "benefits", "host_tax_and_charges", "deductions"
SECTION_TITLES = {
    HOME: "1. Home pay",
    BENEFITS: "2. Assignment benefits",
    HOST: "3. Host tax and employer charges",
    DEDUCTIONS: "4. Deductions",
}


@dataclass
class Line:
    section: str
    key: str
    label: str
    tag: str = ""
    rule_ids: tuple[str, ...] = ()
    amounts: list[Decimal] = field(default_factory=list)   # one per tax year, rounded to the penny

    @property
    def total(self) -> Decimal:
        return sum(self.amounts, ZERO)


@dataclass(frozen=True)
class YearWorking:
    """What a "show working" panel prints for one tax year."""
    label: str
    months: int
    taxable_pay: Decimal          # I
    uk_tax: Decimal               # T
    rounds: int
    trace: Trace
    ahv_extra_base_gbp: Decimal
    ahv_extra_base_chf: Decimal
    grossed_up_ss: Decimal        # E


@dataclass
class Estimate:
    case: Case
    decisions: Decisions
    hypothetical: HypotheticalTax
    year_labels: list[str]
    lines: list[Line]
    subtotals: dict[str, list[Decimal]]
    totals: list[Decimal]
    home_pay: list[Decimal]
    working: list[YearWorking]
    immigration: list[immigration.CostItem]
    assumptions: list[str]

    @property
    def total(self) -> Decimal:
        return sum(self.totals, ZERO)

    @property
    def multiple(self) -> Decimal:
        return self.total / sum(self.home_pay, ZERO)

    def year_multiple(self, i: int) -> Decimal:
        return self.totals[i] / self.home_pay[i]

    @property
    def immigration_total(self) -> Decimal:
        return sum((c.amount for c in self.immigration), ZERO)

    @property
    def all_in(self) -> Decimal:
        """Employer cost plus immigration costs: the figure the duration advice compares."""
        return self.total + self.immigration_total

    @property
    def per_month(self) -> Decimal:
        return self.all_in / self.case.months

    def rule_ids(self) -> list[str]:
        seen: list[str] = []
        for rid in list(self.decisions.rule_ids) + [r for l in self.lines for r in l.rule_ids]:
            if rid not in seen:
                seen.append(rid)
        return seen


def estimate(case: Case, rules: RuleSet | None = None) -> Estimate:
    r = rules or load_rules()
    case.check()
    fx = case.fx_chf_per_gbp
    decisions = decide_all(case, r)
    hypo = hypothetical_tax(case.salary_chf + case.bonus_chf, case.pillar2, r)
    segs = segments(case.months)

    lines: dict[str, Line] = {}

    def add(section, key, label, amount, tag="", rule_ids=()):
        if key not in lines:
            lines[key] = Line(section, key, label, tag, tuple(rule_ids))
        lines[key].amounts.append(pence(amount))

    working = []
    for seg in segs:
        _year(case, seg, decisions, hypo, fx, r, add, working)

    ordered = list(lines.values())
    subtotals = {s: [sum((l.amounts[i] for l in ordered if l.section == s), ZERO) for i in range(len(segs))]
                 for s in SECTION_TITLES}
    totals = [sum(subtotals[s][i] for s in SECTION_TITLES) for i in range(len(segs))]
    return Estimate(
        case=case, decisions=decisions, hypothetical=hypo,
        year_labels=[s.label for s in segs], lines=ordered, subtotals=subtotals,
        totals=totals, home_pay=subtotals[HOME], working=working,
        immigration=immigration.costs(case, r), assumptions=assumptions(case, decisions),
    )


def _year(case: Case, seg: Segment, decisions: Decisions, hypo: HypotheticalTax,
          fx: Decimal, r: RuleSet, add, working: list) -> None:
    share = Decimal(seg.months) / 12
    salary = case.salary_chf / fx * share
    bonus = case.bonus_chf / fx * share
    home = salary + bonus
    hypo_tax = hypo.total / fx * share
    hypo_ss = hypo.social_security / fx * share
    add(HOME, "salary", f"Base salary, CHF {case.salary_chf:,.0f} a year", salary)
    add(HOME, "bonus", f"Bonus, CHF {case.bonus_chf:,.0f} a year", bonus)

    benefit_lines = classify(case, seg, decisions, r)
    for n, b in enumerate(benefit_lines):
        add(BENEFITS, f"benefit_{n}", b.label, b.cost, b.uk_tag, b.rule_ids)
    uk_cash = sum((b.uk_cash for b in benefit_lines), ZERO)
    uk_kind = sum((b.uk_in_kind for b in benefit_lines), ZERO)
    ahv_cash = sum((b.ahv_cash for b in benefit_lines), ZERO)
    ahv_kind = sum((b.ahv_in_kind for b in benefit_lines), ZERO)
    net_home = home - hypo_tax - hypo_ss

    swiss = decisions.social_security.system == SWISS
    if swiss:
        branch = solve_swiss(home_pay=home, hypo_tax=hypo_tax, uk_base=net_home + uk_cash + uk_kind,
                             ahv_cash=ahv_cash, ahv_in_kind=ahv_kind, months=seg.months, fx=fx,
                             full_base=case.ahv_full_base, rules=r)
        tax, trace, i = branch.tax, branch.trace, branch.taxable_pay
        ni_ee = ni_er = c1a = ZERO
        ch_er = employer_contributions(home, r, seg.months, chf_per_unit=fx)
        ch_ee = employee_contributions(home, r, seg.months, chf_per_unit=fx)
        ch_extra = branch.extra_employee_ss + branch.extra_employer_ss
        extra_base, e = branch.ahv_extra_base, branch.grossed_up_ss
    else:
        branch = solve_uk(cash=net_home + uk_cash, in_kind=uk_kind, months=seg.months, rules=r)
        tax, trace, i = branch.tax, branch.trace, branch.taxable_pay
        ni_ee = branch.employee_ni
        ni_er = nic_employer(net_home + uk_cash + tax + ni_ee, seg.months, r)
        c1a = class_1a(uk_kind, r)
        ch_er = ch_ee = ch_extra = extra_base = e = ZERO

    add(HOST, "uk_tax", "UK income tax, including tax on tax", tax, rule_ids=INCOME_TAX_RULES + ("UK-TE-01", "UK-TE-02"))
    add(HOST, "uk_ni", "UK National Insurance: employee, employer and Class 1A", ni_ee + ni_er + c1a,
        rule_ids=("UK-NI-01", "UK-NI-02", "UK-NI-03") if not swiss else ("SS-UK-01",))
    add(HOST, "ch_er", "Swiss social security on home pay, employer share", ch_er, rule_ids=("CH-SS-01", "CH-SS-02"))
    add(HOST, "ch_ee", "Swiss social security on home pay, employee share paid by the employer", ch_ee,
        rule_ids=("CH-SS-01", "CH-SS-02"))
    add(HOST, "ch_extra", "Swiss AHV/IV/EO on the assignment extras, both shares", ch_extra,
        rule_ids=("CH-AHV-01", "CH-AHV-02", "CH-AHV-03", "UK-BEN-07"))
    add(DEDUCTIONS, "hypo_tax", f"Hypothetical Swiss income tax, CHF {pence(hypo.total):,} a year", -hypo_tax,
        rule_ids=HYPO_TAX_RULES)
    add(DEDUCTIONS, "hypo_ss", f"Hypothetical Swiss social security, CHF {pence(hypo.social_security):,} a year",
        -hypo_ss, rule_ids=("CH-SS-01", "CH-SS-02"))

    working.append(YearWorking(seg.label, seg.months, i, tax, trace.count, trace,
                               extra_base, extra_base * fx, e))


def assumptions(case: Case, d: Decisions) -> list[str]:
    out = [
        f"The stay runs {case.months} months from 6 April 2026; {d.social_security.reason}.",
        d.relief_reason + ".",
        "UK 2026/27 rates for every tax year, England and Northern Ireland bands. The employee is UK "
        "resident until departure, has no other UK income and works only in the UK; a part tax year "
        "keeps the full personal allowance (split-year treatment).",
        "Hypothetical tax is the Swiss 2026 federal, cantonal (95%) and city of Zurich (119%) income tax of a "
        "single person: no church tax, no Personalsteuer, flat deductions"
        + (" with the pillar-2 insurance allowances" if case.pillar2 else " without pillar 2") + ", no BVG.",
        "Hypothetical social security is the employee's AHV/IV/EO and ALV only; BVG, family-allowance and "
        "accident contributions are left out. Hypothetical figures for a part year are the annual ones pro rata.",
    ]
    if d.social_security.system == SWISS and case.ahv_full_base:
        out.append("Swiss AHV is due on the UK tax the employer bears above the hypothetical tax, on cash "
                   "allowances and on housing; the employer bears both shares, and the extra employee share "
                   "is UK taxable pay"
                   + (". Housing is left out for the first 12 months because a Swiss home is kept."
                      if case.swiss_home_kept else "."))
    elif d.social_security.system == SWISS:
        out.append("Swiss AHV is due on salary and bonus only (literal reading of the brief).")
    else:
        out.append("The Apprenticeship Levy is not charged: the UK subsidiary's pay bill is assumed under £3 million.")
    out.append(f"One exchange rate, CHF {case.fx_chf_per_gbp} per £1, for every CHF amount in every year.")
    out.append("Immigration costs are shown separately and in the duration advice, not in this table.")
    out.append("Each line is rounded to the penny before it is added.")
    return out


def literal_reading(case: Case) -> Case:
    """The candidate pack read literally: housing taxable, Swiss AHV on salary and bonus only."""
    return replace(case, ahv_full_base=False, twr_rule=False)
