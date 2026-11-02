"""Immigration requirements, eligibility and timeline for the immigration tab (subtask 15).

The texts live in rules/requirements_2026.json. They hold no typed numbers: a placeholder
such as {gbp:IMM-WP-04.per_year} is filled from the rules file, so every figure on the tab
comes from a rule with an official source (checks 2, 3 and 9).

Rule IDs: IMM-WP-01 to 04, IMM-BV-01 to 02, IMM-PP-01 to 02, IMM-SP-01 to 04, IMM-RTW-01,
DUR-04 to 06.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from .rules import RulesError, RuleSet, load_rules

DEFAULT_REQUIREMENTS_FILE = Path(__file__).resolve().parent.parent / "rules" / "requirements_2026.json"
PLACEHOLDER = re.compile(r"\{(gbp|chf|n):([A-Z0-9-]+)\.([a-z0-9_]+)\}")
AREAS = ("work_permit", "business_visit", "passport", "company")
COST_KEYS = ("sponsor_licence", "certificate", "skills_charge", "visa_fee", "health_surcharge", "eta")
MET, NOT_MET, TO_CHECK, UNKNOWN = "met", "not met", "to check", "not checked"


# ---------------------------------------------------------------- texts

def _number(value: Decimal) -> str:
    return f"{value:,.0f}" if value == value.to_integral_value() else f"{value:,.2f}"


def fill(text: str | None, rules: RuleSet) -> str | None:
    """Replace every {kind:RULE-ID.field} with the rule's value."""
    if text is None:
        return None

    def sub(m: re.Match) -> str:
        kind, rule_id, field = m.groups()
        value = Decimal(rules[rule_id][field])
        number = _number(value)
        return {"gbp": f"£{number}", "chf": f"CHF {number}", "n": number}[kind]

    return PLACEHOLDER.sub(sub, text)


@dataclass(frozen=True)
class Requirement:
    id: str
    area: str
    text: str
    time: str | None
    cost_key: str | None
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class Area:
    key: str
    title: str
    items: tuple[Requirement, ...]


@dataclass(frozen=True)
class Requirements:
    title: str
    summary: str
    route_rule_ids: tuple[str, ...]
    nationality: str
    home_country: str
    host_country: str
    areas: tuple[Area, ...]
    timeline: tuple[dict, ...]

    def rule_ids(self) -> list[str]:
        out: list[str] = list(self.route_rule_ids)
        for area in self.areas:
            for item in area.items:
                out += item.rule_ids
        for step in self.timeline:
            out += step["rule_ids"]
        return list(dict.fromkeys(out))


def validate(data: dict, rules: RuleSet) -> list[str]:
    """Return every problem in a requirements file; an empty list means it is valid."""
    errors: list[str] = []

    def check_rule_ids(where: str, ids) -> None:
        if not ids:
            errors.append(f"{where} cites no rule")
        for rid in ids or ():
            if rid not in rules:
                errors.append(f"{where} cites unknown rule {rid}")

    def check_text(where: str, text) -> None:
        if text is None:
            return
        for m in PLACEHOLDER.finditer(text):
            try:
                Decimal(rules[m.group(2)][m.group(3)])
            except (RulesError, ArithmeticError, TypeError, ValueError):
                errors.append(f"{where}: placeholder {m.group(0)} has no value in the rules")
        if re.search(r"\{[^}]*\}", PLACEHOLDER.sub("", text)):
            errors.append(f"{where}: malformed placeholder")

    route = data.get("route") or {}
    for key in ("title", "summary", "nationality", "home_country", "host_country"):
        if not route.get(key):
            errors.append(f"route has no {key}")
    check_rule_ids("route", route.get("rule_ids"))

    areas = data.get("areas") or []
    if [a.get("key") for a in areas] != list(AREAS):
        errors.append(f"areas must be {', '.join(AREAS)} in that order")
    seen: set[str] = set()
    for area in areas:
        for item in area.get("items") or []:
            iid = item.get("id", "?")
            if iid in seen:
                errors.append(f"requirement {iid} appears twice")
            seen.add(iid)
            if not item.get("text"):
                errors.append(f"requirement {iid} has no text")
            check_text(f"requirement {iid}", item.get("text"))
            check_text(f"requirement {iid} time", item.get("time"))
            if item.get("cost_key") not in (None,) + COST_KEYS:
                errors.append(f"requirement {iid} has unknown cost_key {item.get('cost_key')}")
            check_rule_ids(f"requirement {iid}", item.get("rule_ids"))

    steps = data.get("timeline") or []
    ids = [s.get("id") for s in steps]
    for i, step in enumerate(steps):
        sid = step.get("id", "?")
        for dep in step.get("after", []):
            if dep not in ids[:i]:
                errors.append(f"timeline step {sid} waits for {dep}, which is not an earlier step")
        if step.get("duration"):
            rule_id, _, field = step["duration"].partition(".")
            try:
                Decimal(rules[rule_id][field])
            except (RulesError, ArithmeticError, TypeError, ValueError):
                errors.append(f"timeline step {sid}: duration {step['duration']} has no value in the rules")
        if step.get("unit") not in ("weeks", "working days"):
            errors.append(f"timeline step {sid}: unit must be weeks or working days")
        check_rule_ids(f"timeline step {sid}", step.get("rule_ids"))
    return errors


def load_requirements(path: str | Path | None = None, rules: RuleSet | None = None) -> Requirements:
    if path is None and rules is None:
        return _default()
    r = rules or load_rules()
    with open(path or DEFAULT_REQUIREMENTS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    return _build(data, r, str(path or DEFAULT_REQUIREMENTS_FILE.name))


@lru_cache(maxsize=1)
def _default() -> Requirements:
    with open(DEFAULT_REQUIREMENTS_FILE, encoding="utf-8") as fh:
        data = json.load(fh)
    return _build(data, load_rules(), DEFAULT_REQUIREMENTS_FILE.name)


def _build(data: dict, rules: RuleSet, origin: str) -> Requirements:
    errors = validate(data, rules)
    if errors:
        raise RulesError(f"{origin}: " + "; ".join(errors))
    route = data["route"]
    areas = tuple(
        Area(a["key"], a["title"], tuple(
            Requirement(i["id"], a["key"], fill(i["text"], rules), fill(i.get("time"), rules),
                        i.get("cost_key"), tuple(i["rule_ids"]))
            for i in a["items"]))
        for a in data["areas"]
    )
    return Requirements(route["title"], route["summary"], tuple(route["rule_ids"]), route["nationality"],
                        route["home_country"], route["host_country"], areas, tuple(data["timeline"]))


# ---------------------------------------------------------------- eligibility

@dataclass(frozen=True)
class EligibilityCheck:
    test: str
    status: str          # met, not met, to check, not checked
    detail: str
    rule_ids: tuple[str, ...]


@dataclass(frozen=True)
class Eligibility:
    status: str
    summary: str
    checks: tuple[EligibilityCheck, ...]


def eligibility(*, salary_gbp: Decimal | None, months_with_employer: int | None,
                licence_held: bool, rules: RuleSet | None = None) -> Eligibility:
    """Senior or Specialist Worker tests the tool can check from the inputs (IMM-WP-01).

    The salary test uses base salary only, a cautious reading: the bonus is not guaranteed.
    """
    r = rules or load_rules()
    wp = r["IMM-WP-01"]
    min_salary, waived_from = wp["min_salary"], wp["prior_service_waived_from"]
    prior = int(wp["prior_service_months"])
    checks = []

    checks.append(EligibilityCheck(
        "Sponsored by a UK employer with a sponsor licence",
        MET if licence_held else TO_CHECK,
        "The UK subsidiary already holds a licence." if licence_held
        else "The UK subsidiary must get a sponsor licence first (see the timeline).",
        ("IMM-WP-01", "IMM-SP-01")))

    if salary_gbp is None:
        checks.append(EligibilityCheck("Salary at least the minimum", UNKNOWN,
                                       "No salary given.", ("IMM-WP-01",)))
    else:
        ok = salary_gbp >= min_salary
        checks.append(EligibilityCheck(
            f"Salary at least £{_number(min_salary)}",
            MET if ok else NOT_MET,
            f"Base salary £{salary_gbp:,.2f} a year (bonus not counted).", ("IMM-WP-01",)))

    checks.append(EligibilityCheck(
        "Eligible occupation, paid at least its going rate", TO_CHECK,
        "Depends on the occupation code of the UK role; check it against the going rates.",
        ("IMM-WP-01",)))

    if salary_gbp is not None and salary_gbp >= waived_from:
        checks.append(EligibilityCheck(
            f"{prior} months with the employer outside the UK", MET,
            f"Not required: base salary is £{_number(waived_from)} or more.", ("IMM-WP-01",)))
    elif months_with_employer is None:
        checks.append(EligibilityCheck(f"{prior} months with the employer outside the UK", UNKNOWN,
                                       "Months with the employer not given.", ("IMM-WP-01",)))
    else:
        ok = months_with_employer >= prior
        checks.append(EligibilityCheck(
            f"{prior} months with the employer outside the UK", MET if ok else NOT_MET,
            f"{months_with_employer} months with the employer.", ("IMM-WP-01",)))

    statuses = [c.status for c in checks]
    if NOT_MET in statuses:
        status, summary = NOT_MET, "Not eligible on the inputs given: see the tests marked not met."
    elif UNKNOWN in statuses:
        status, summary = UNKNOWN, "Not fully checked: some inputs are missing."
    elif TO_CHECK in statuses:
        status, summary = TO_CHECK, "Eligible on the inputs given; the items marked to check still need confirming."
    else:
        status, summary = MET, "Eligible on the inputs given."
    return Eligibility(status, summary, tuple(checks))


# ---------------------------------------------------------------- timeline

@dataclass(frozen=True)
class Step:
    id: str
    step: str
    party: str
    duration: Decimal          # in its own unit
    unit: str
    start_week: Decimal
    end_week: Decimal
    skipped: bool
    rule_ids: tuple[str, ...]


def timeline(*, licence_held: bool, requirements: Requirements | None = None,
             rules: RuleSet | None = None) -> tuple[list[Step], Decimal]:
    """Earliest start and end of each step, in weeks from today; returns the steps and the total."""
    r = rules or load_rules()
    req = requirements or load_requirements()
    ends: dict[str, Decimal] = {}
    steps = []
    for s in req.timeline:
        skipped = bool(s["skip_if_licence_held"] and licence_held)
        if s["duration"] and not skipped:
            rule_id, _, field = s["duration"].partition(".")
            duration = Decimal(r[rule_id][field])
        else:
            duration = Decimal(0)
        weeks = duration / 5 if s["unit"] == "working days" else duration
        start = max((ends[d] for d in s["after"]), default=Decimal(0))
        ends[s["id"]] = start + weeks
        steps.append(Step(s["id"], s["step"], s["party"], duration, s["unit"], start, start + weeks,
                          skipped, tuple(s["rule_ids"])))
    return steps, max(ends.values())
