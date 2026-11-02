"""The planned length and the rules it switches (spec section 17).

Rule ID DUR-01 (temporary-workplace relief), the social security decision, and the
split of the stay into UK tax years.
"""
from __future__ import annotations

from dataclasses import dataclass

from .inputs import Case
from .rules import RuleSet, load_rules
from .social_security import SocialSecurityDecision, decide

FIRST_TAX_YEAR = 2026   # the rules cover UK tax year 2026/27, which starts on 6 April 2026
MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December")


def month_date(offset: int, day: int = 6) -> tuple[int, int, int]:
    """(year, month, day) of the 6th of the month `offset` months after April 2026."""
    n = 3 + offset                       # April is month index 3
    return FIRST_TAX_YEAR + n // 12, n % 12 + 1, day


def date_text(offset: int, day: int = 6) -> str:
    y, mo, d = month_date(offset, day)
    return f"{d} {MONTH_NAMES[mo - 1]} {y}"


@dataclass(frozen=True)
class Segment:
    """The part of the stay inside one UK tax year (6 April to 5 April)."""
    index: int           # 0 for the first tax year of the stay (2026/27)
    months: int          # months of the stay in this tax year
    months_before: int   # months of the stay before this tax year
    start_offset: int    # months from 6 April 2026 to this segment's first day

    @property
    def label(self) -> str:
        start = FIRST_TAX_YEAR + self.index
        return f"{start}/{(start + 1) % 100:02d}"

    @property
    def is_first(self) -> bool:
        return self.months_before == 0

    @property
    def period(self) -> str:
        """For example "6 October 2026 to 5 April 2027"."""
        return f"{date_text(self.start_offset)} to {date_text(self.start_offset + self.months, 5)}"

    @property
    def rates_assumed(self) -> bool:
        """True for tax years after 2026/27: the rules file holds 2026/27 rates only."""
        return self.index > 0


def segments(months: int, start_offset: int = 0) -> list[Segment]:
    """Split the stay into UK tax years.

    start_offset is the number of months from 6 April 2026 to the start (0 to 11), so a
    stay from 6 October 2026 has a first part year of 6 months.
    """
    out, left, k, before = [], months, 0, 0
    room = 12 - start_offset             # months left in the first tax year
    while left > 0:
        m = min(room, left)
        out.append(Segment(k, m, before, start_offset + before))
        left -= m
        before += m
        k += 1
        room = 12
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
        relief, why = False, "No relief: the temporary-workplace relief setting is off"
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

