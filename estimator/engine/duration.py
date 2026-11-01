"""The planned length and the rules it switches (spec section 17).

Rule ID DUR-01 (temporary-workplace relief), the social security decision, and the
split of the stay into UK tax years.
"""
from __future__ import annotations

from dataclasses import dataclass

from .inputs import Case
from .rules import RuleSet, load_rules
from .social_security import SocialSecurityDecision, decide

FIRST_TAX_YEAR = 2026   # the stay starts on 6 April 2026


@dataclass(frozen=True)
class Segment:
    """The part of the stay inside one UK tax year."""
    index: int           # 0 for the first tax year
    months: int          # months worked in this tax year (12, or fewer in the last one)
    months_before: int   # months of the stay before this tax year

    @property
    def label(self) -> str:
        start = FIRST_TAX_YEAR + self.index
        return f"{start}/{(start + 1) % 100:02d}"

    @property
    def is_first(self) -> bool:
        return self.index == 0


def segments(months: int) -> list[Segment]:
    out, left, k = [], months, 0
    while left > 0:
        m = min(12, left)
        out.append(Segment(k, m, 12 * k))
        left -= m
        k += 1
    return out


@dataclass(frozen=True)
class Decisions:
    relief: bool
    relief_reason: str
    social_security: SocialSecurityDecision
    rule_ids: tuple[str, ...]


def decide_all(case: Case, rules: RuleSet | None = None) -> Decisions:
    r = rules or load_rules()
    limit = int(r["DUR-01"]["max_months"])
    if not case.twr_rule:
        relief, why = False, "Temporary-workplace relief not applied (literal reading)"
    elif not case.continuing_employment:
        relief, why = False, "No relief: the UK post is a new employment, not a secondment"
    elif not case.housing_reasonable:
        relief, why = False, "No relief: housing not reasonable for one person"
    elif case.months > limit:
        relief, why = False, f"No relief: stay planned for more than {limit} months"
    else:
        relief, why = True, f"Temporary workplace: stay planned for {case.months} months, no more than {limit}"
    ss = decide(case, r)
    return Decisions(relief, why, ss, ("DUR-01", "UK-BEN-02", "UK-BEN-08") + ss.rule_ids)

