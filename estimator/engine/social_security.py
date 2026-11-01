"""Which social security system applies during the posting (subtask 9).

Rule IDs: SS-CONV-01 to 04, DUR-02, DUR-03, SS-CH-01, SS-UK-01. The tests run in order;
the first one that fails sends the case to UK National Insurance (Article 13).
"""
from __future__ import annotations

from dataclasses import dataclass

from .inputs import Case
from .rules import RuleSet, load_rules

SWISS, UK = "CH", "UK"


@dataclass(frozen=True)
class Check:
    test: str
    passed: bool
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class SocialSecurityDecision:
    system: str                  # "CH" or "UK"
    reason: str
    checks: tuple[Check, ...]
    rule_ids: tuple[str, ...]


def decide(case: Case, rules: RuleSet | None = None) -> SocialSecurityDecision:
    r = rules or load_rules()
    posting_limit = int(r["SS-CONV-02"]["max_months"])
    exception_limit = int(r["SS-CONV-03"]["max_months"])
    prior = int(r["SS-CONV-04"]["min_prior_insurance_months"])

    checks = [
        Check("Sent by a Swiss employer, direct employment relationship kept",
              case.continuing_employment, ("SS-CONV-02", "SS-CONV-04")),
        Check(f"Insured in Switzerland for at least {prior} month before the posting",
              case.months_with_employer >= prior, ("SS-CONV-04",)),
        Check(f"Planned length no more than {posting_limit} months",
              case.months <= posting_limit, ("SS-CONV-02", "DUR-02")),
    ]
    if all(c.passed for c in checks):
        return SocialSecurityDecision(
            SWISS, f"Article 14: posting of {case.months} months, certificate of coverage needed",
            tuple(checks), ("SS-CONV-02", "SS-CONV-04", "DUR-02", "SS-CH-01", "SS-UK-01"))

    only_length_failed = all(c.passed for c in checks[:2])
    if only_length_failed:
        exception = Check(f"Article 17 exception agreed (up to {exception_limit} months)",
                          case.art17_exception and case.months <= exception_limit,
                          ("SS-CONV-03", "DUR-03"))
        checks.append(exception)
        if exception.passed:
            return SocialSecurityDecision(
                SWISS, "Article 17 exception agreed by both authorities",
                tuple(checks), ("SS-CONV-03", "DUR-03", "SS-CH-01", "SS-UK-01"))

    failed = next(c for c in checks if not c.passed)
    return SocialSecurityDecision(
        UK, f"UK National Insurance from day one (Article 13): {failed.test.lower()} is not met",
        tuple(checks), ("SS-CONV-01",) + failed.rule_ids)
