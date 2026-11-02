"""Method switches and alternative calculations, explained (spec sections 11, 16, 17).

The tool's default method applies two decisions of 1 November 2026:
- temporary-workplace relief for the London housing when the stay is planned for
  24 months or less (DUR-01, UK-BEN-02, UK-BEN-08), and
- Swiss AHV on the full assignment pay, not only salary and bonus (CH-AHV-01 to 03,
  UK-BEN-07).

Each alternative switches one or both off and is calculated in full, so the front end can
show what was taken into account, the totals, and which lines move and by how much.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal

from .cost_table import Estimate, estimate
from .inputs import Case
from .money import ZERO
from .rules import RuleSet, load_rules


@dataclass(frozen=True)
class Switch:
    key: str                 # the Case field
    label: str
    on: str                  # what the method does when the switch is on
    off: str                 # what it does when off
    rule_ids: tuple[str, ...]
    default: bool = True


SWITCHES = (
    Switch(
        "twr_rule", "Temporary-workplace relief for housing",
        on="Housing and temporary housing are not taxable in the UK while the stay is planned for 24 months "
           "or less, the Swiss contract continues and the housing is reasonable: the costs are those of a "
           "temporary workplace, matched by a full deduction.",
        off="Housing is a taxable benefit in kind in the UK, and temporary housing shares the £8,000 "
            "relocation exemption, so the employer also pays UK tax (and tax on tax) on it.",
        rule_ids=("DUR-01", "UK-BEN-01", "UK-BEN-02", "UK-BEN-03", "UK-BEN-08")),
    Switch(
        "ahv_full_base", "Swiss AHV on the full assignment pay",
        on="Swiss AHV/IV/EO is due on everything the employer pays for the assignment: the UK tax it bears "
           "above the hypothetical tax, cash allowances and housing. The employer bears both shares; the "
           "employee share it pays is itself UK taxable pay.",
        off="Swiss AHV/IV/EO is due on salary and bonus only, as a literal reading of the brief suggests.",
        rule_ids=("CH-AHV-01", "CH-AHV-02", "CH-AHV-03", "UK-BEN-07")),
    Switch(
        "pillar2", "Employee pays into pillar 2",
        on="The hypothetical Swiss tax uses the lower insurance allowance for people with a pension fund.",
        off="The hypothetical Swiss tax uses the higher insurance allowance for people without one.",
        rule_ids=("CH-TAX-02", "CH-TAX-05")),
)
SWITCH_BY_KEY = {s.key: s for s in SWITCHES}


@dataclass(frozen=True)
class SwitchState:
    switch: Switch
    value: bool

    @property
    def is_default(self) -> bool:
        return self.value == self.switch.default

    @property
    def explanation(self) -> str:
        return self.switch.on if self.value else self.switch.off


def switch_states(case: Case) -> list[SwitchState]:
    return [SwitchState(s, getattr(case, s.key)) for s in SWITCHES]


@dataclass(frozen=True)
class AlternativeDef:
    key: str
    title: str
    summary: str
    settings: dict           # Case fields it changes


ALTERNATIVES = (
    AlternativeDef("default_method", "Tool's default method",
                   "Both decisions applied: housing relief and Swiss AHV on the full assignment pay.",
                   {"twr_rule": True, "ahv_full_base": True}),
    AlternativeDef("literal_reading", "Literal reading of the brief",
                   "Housing taxed in the UK as a benefit in kind and Swiss AHV on salary and bonus only, as the "
                   "candidate pack reads at face value.",
                   {"twr_rule": False, "ahv_full_base": False}),
    AlternativeDef("without_relief", "Without temporary-workplace relief",
                   "Only the housing relief switched off; Swiss AHV stays on the full assignment pay.",
                   {"twr_rule": False, "ahv_full_base": True}),
    AlternativeDef("salary_only_ahv", "Swiss AHV on salary and bonus only",
                   "Only the AHV base switched to salary and bonus; the housing relief stays.",
                   {"twr_rule": True, "ahv_full_base": False}),
)


@dataclass(frozen=True)
class LineDifference:
    key: str
    label: str
    main: Decimal
    alternative: Decimal
    main_tag: str = ""
    alternative_tag: str = ""

    @property
    def difference(self) -> Decimal:
        return self.alternative - self.main


@dataclass(frozen=True)
class Alternative:
    definition: AlternativeDef
    changed: list[SwitchState]       # the switches that differ from the main calculation
    result: Estimate
    difference: Decimal              # alternative total minus main total
    year_differences: list[Decimal]
    lines: list[LineDifference]      # only lines whose amount or UK tag changes
    relief_reason: str
    social_security_reason: str


def _line_totals(e: Estimate) -> dict[str, tuple[str, Decimal, str]]:
    return {l.key: (l.label, l.total, l.tag) for l in e.lines}


def alternatives(case: Case, main: Estimate | None = None, rules: RuleSet | None = None) -> list[Alternative]:
    """Every alternative whose settings differ from the case's own, calculated in full."""
    r = rules or load_rules()
    main = main or estimate(case, r)
    base = _line_totals(main)
    out = []
    for d in ALTERNATIVES:
        if all(getattr(case, k) == v for k, v in d.settings.items()):
            continue
        alt_case = replace(case, **d.settings)
        e = estimate(alt_case, r)
        alt_lines = _line_totals(e)
        lines = []
        for key in list(dict.fromkeys(list(base) + list(alt_lines))):
            m_label, m, m_tag = base.get(key, ("", ZERO, ""))
            a_label, a, a_tag = alt_lines.get(key, (m_label, ZERO, ""))
            if a != m or a_tag != m_tag:
                lines.append(LineDifference(key, a_label or m_label, m, a, m_tag, a_tag))
        changed = [SwitchState(SWITCH_BY_KEY[k], v) for k, v in d.settings.items() if getattr(case, k) != v]
        out.append(Alternative(
            d, changed, e, e.total - main.total,
            [a - m for a, m in zip(e.totals, main.totals)], lines,
            e.decisions.relief_reason, e.decisions.social_security.reason))
    return out
