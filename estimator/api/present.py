"""Turn engine results into JSON-ready dicts (subtasks 14 and 15).

Money goes out as strings with two decimals ("527121.55"), exact and ready to format.
Every figure carries the rule IDs it used, and every rule ID resolves to its official
sources in the response's "rules" block, so the front end can link each figure (check 3).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from ..engine.advice import Advice, Row
from ..engine.alternatives import Alternative, SwitchState
from ..engine.cost_table import SECTION_TITLES, Estimate
from ..engine.money import pence, round_down
from ..engine.requirements import Eligibility, Requirements, Step
from ..engine.rules import RuleSet
from ..engine.social_security import SWISS
from ..engine.swiss_tax import HYPO_TAX_RULES, HypotheticalTax

SYSTEM_NAMES = {SWISS: "Swiss social security", "UK": "UK National Insurance"}


def m(x: Decimal) -> str:
    """Money to a string with two decimals."""
    return str(pence(x))


def ratio(x: Decimal) -> str:
    return str(x.quantize(Decimal("0.01"), ROUND_HALF_UP))


class Citations:
    """Collects every rule ID used in a response and resolves it once at the end."""

    def __init__(self, rules: RuleSet):
        self.rules = rules
        self.ids: list[str] = []

    def use(self, ids) -> list[str]:
        ids = list(dict.fromkeys(ids))
        self.ids.extend(i for i in ids if i not in self.ids)
        return ids

    def sources(self, ids) -> list[dict]:
        """Unique official pages behind some rule IDs, for a link beside a figure."""
        seen, out = set(), []
        for rid in self.use(ids):
            for s in self.rules[rid].sources:
                if s.url not in seen:
                    seen.add(s.url)
                    out.append({"title": s.title, "url": s.url})
        return out

    def block(self) -> dict:
        return {c["rule_id"]: c for c in self.rules.citations(self.ids)}


# ---------------------------------------------------------------- estimate

def settings(states: list[SwitchState], cite: Citations) -> list[dict]:
    return [{
        "key": s.switch.key, "label": s.switch.label, "value": s.value, "default": s.switch.default,
        "is_default": s.is_default, "explanation": s.explanation,
        "rule_ids": cite.use(s.switch.rule_ids),
    } for s in states]


def decisions(e: Estimate, cite: Citations) -> dict:
    d, ss = e.decisions, e.decisions.social_security
    return {
        "relief": {"applies": d.relief, "reason": d.relief_reason,
                   "rule_ids": cite.use(("DUR-01", "UK-BEN-02", "UK-BEN-08"))},
        "social_security": {
            "system": ss.system, "system_name": SYSTEM_NAMES[ss.system], "reason": ss.reason,
            "checks": [{"test": c.test, "passed": c.passed, "rule_ids": cite.use(c.rule_ids)} for c in ss.checks],
            "rule_ids": cite.use(ss.rule_ids),
        },
    }


def cost_table(e: Estimate, cite: Citations) -> dict:
    sections = []
    for key, title in SECTION_TITLES.items():
        lines = [{
            "key": l.key, "label": l.label, "tag": l.tag,
            "amounts": [m(a) for a in l.amounts], "total": m(l.total),
            # a line without rules is the user's own input (salary, bonus, a benefit's cost)
            "basis": "rules" if l.rule_ids else "input",
            "rule_ids": cite.use(l.rule_ids), "sources": cite.sources(l.rule_ids),
        } for l in e.lines if l.section == key]
        sections.append({"key": key, "title": title, "lines": lines,
                         "subtotals": [m(x) for x in e.subtotals[key]],
                         "total": m(sum(e.subtotals[key], Decimal(0)))})
    return {
        "currency": "GBP",
        "years": [{"label": seg.label, "months": seg.months, "period": seg.period,
                   "rates_assumed": seg.rates_assumed,
                   "rates_note": ("Uses the 2026/27 rates: the rules file has no later tax year yet."
                                  if seg.rates_assumed else "2026/27 rates from the official sources.")}
                  for seg in e.segments],
        "sections": sections,
        "totals": [m(t) for t in e.totals],
        "total": m(e.total),
        "home_pay": [m(h) for h in e.home_pay],
        "home_pay_total": m(sum(e.home_pay, Decimal(0))),
        "multiple": ratio(e.multiple),
        "year_multiples": [ratio(e.year_multiple(i)) for i in range(len(e.totals))],
    }


def hypothetical_tax(h: HypotheticalTax, cite: Citations) -> dict:
    return {
        "currency": "CHF",
        "gross": m(h.gross), "social_security": m(h.social_security), "net_salary": m(h.net_salary),
        "federal_taxable": m(h.federal_taxable), "zurich_taxable": m(h.zurich_taxable),
        "federal": m(h.federal), "zurich_basic": m(h.basic),
        "cantonal": m(h.cantonal), "communal": m(h.communal), "total": m(h.total),
        "rule_ids": cite.use(HYPO_TAX_RULES + ("CH-SS-01", "CH-SS-02")),
        "sources": cite.sources(HYPO_TAX_RULES),
    }


def check_figure(h: HypotheticalTax, rules: RuleSet, cite: Citations) -> dict | None:
    """Check 15: the hypothetical Swiss tax beside the official ESTV calculator (CH-TAX-10).

    Only shown when the taxable incomes, rounded down to the tariff step, are the ones the
    calculator was run with.
    """
    ref, step = rules["CH-TAX-10"], rules["CH-TAX-03"]["income_step"]
    if (round_down(h.zurich_taxable, step) != ref["cantonal_taxable"]
            or round_down(h.federal_taxable, step) != ref["federal_taxable"]):
        return None
    parts = []
    for key, label, ours in (("federal", "Federal income tax", h.federal),
                             ("cantonal", "Cantonal income tax, Zurich (95%)", h.cantonal),
                             ("communal", "City of Zurich income tax (119%)", h.communal)):
        parts.append({"label": label, "tool": m(ours), "official": m(ref[key]),
                      "difference": m(ours - ref[key])})
    official_total = ref["federal"] + ref["cantonal"] + ref["communal"]
    return {
        "title": "Hypothetical Swiss tax against the official ESTV tax calculator",
        "currency": "CHF",
        "parts": parts,
        "tool_total": m(h.total),
        "official_total": m(official_total),
        "difference": m(h.total - official_total),
        "note": "The calculator shows whole francs and adds the CHF 24 Personalsteuer, which the hypothetical "
                f"tax leaves out; its total including that is CHF {ref['total']:,}.",
        "how_to_check": [
            "Open the ESTV tax calculator (link below) and choose the income and wealth tax for tax year 2026.",
            "Place of residence: 8001 Zürich. A single person, no children, no church affiliation.",
            f"Enter the taxable income: CHF {ref['cantonal_taxable']:,} for cantonal and municipal tax and "
            f"CHF {ref['federal_taxable']:,} for federal tax: the tool's taxable incomes under Show working, rounded "
            "down to CHF 100 as the tariffs do.",
            f"The calculator shows federal tax CHF {ref['federal']:,}, cantonal tax CHF {ref['cantonal']:,} and "
            f"municipal tax CHF {ref['communal']:,}, plus the CHF {rules['CH-TAX-08']['amount']:,} Personalsteuer.",
        ],
        "rule_ids": cite.use(("CH-TAX-10",)),
        "sources": cite.sources(("CH-TAX-10",)),
    }


def working(e: Estimate, cite: Citations) -> list[dict]:
    swiss = e.decisions.social_security.system == SWISS
    formula = ("T = UKTax(I + T); Swiss AHV on the assignment extras is solved in the same loop"
               if swiss else "G = UKTax(I + G) + employee NI(C + G)")
    out = []
    for w in e.working:
        rounds = w.trace.rounds
        out.append({
            "label": w.label, "months": w.months, "formula": formula,
            "taxable_pay": m(w.taxable_pay), "uk_tax": m(w.uk_tax), "rounds": w.rounds,
            "trace": [{"round": n, "value": m(v)} for n, v in rounds],
            "last_change": m(abs(rounds[-1][1] - rounds[-2][1])) if len(rounds) > 1 else m(rounds[-1][1]),
            "ahv_extra_base_gbp": m(w.ahv_extra_base_gbp), "ahv_extra_base_chf": m(w.ahv_extra_base_chf),
            "grossed_up_social_security": m(w.grossed_up_ss),
            "rule_ids": cite.use(("UK-TE-01", "UK-TE-02") + (("CH-AHV-01", "CH-AHV-02", "UK-BEN-07") if swiss
                                                             else ("UK-NI-01",))),
        })
    return out


def alternatives(alts: list[Alternative], main: Estimate, cite: Citations) -> list[dict]:
    out = []
    for a in alts:
        e = a.result
        out.append({
            "key": a.definition.key, "title": a.definition.title, "summary": a.definition.summary,
            "changed": [{"key": s.switch.key, "label": s.switch.label, "value": s.value,
                         "explanation": s.explanation, "rule_ids": cite.use(s.switch.rule_ids)}
                        for s in a.changed],
            "totals": [m(t) for t in e.totals], "total": m(e.total), "multiple": ratio(e.multiple),
            "difference": m(a.difference), "year_differences": [m(x) for x in a.year_differences],
            "lines": [{"key": l.key, "label": l.label, "main": m(l.main), "alternative": m(l.alternative),
                       "difference": m(l.difference), "main_tag": l.main_tag, "alternative_tag": l.alternative_tag}
                      for l in a.lines],
            "relief_reason": a.relief_reason,
            "social_security_reason": a.social_security_reason,
        })
    return out


def immigration_costs(e: Estimate, cite: Citations) -> dict:
    items = [{"key": c.key, "label": c.label, "amount": m(c.amount), "paid_by": c.paid_by,
              "rule_ids": cite.use(c.rule_ids), "sources": cite.sources(c.rule_ids)} for c in e.immigration]
    by = lambda who: m(sum((c.amount for c in e.immigration if c.paid_by == who), Decimal(0)))  # noqa: E731
    return {"items": items, "total": m(e.immigration_total), "sponsor_total": by("sponsor"),
            "employee_total": by("employee")}


def _row(r: Row) -> dict:
    return {"months": r.months, "social_security": r.social_security, "relief": r.relief,
            "employer_cost": m(r.employer_cost), "immigration": m(r.immigration),
            "all_in": m(r.all_in), "per_month": m(r.per_month)}


def advice(a: Advice, lo: int, hi: int, cite: Citations) -> dict:
    return {
        "range": {"from": lo, "to": hi},
        "planned": _row(a.planned),
        "cheapest": _row(a.cheapest),
        "cheapest_from_planned": _row(a.cheapest_from_planned),
        "next_month": _row(a.next_month) if a.next_month else None,
        "next_month_extra": m(a.next_month_extra) if a.next_month_extra is not None else None,
        "thresholds_crossed": a.thresholds_crossed,
        "rows": [_row(r) for r in a.rows],
        "rule_ids": cite.use(("DUR-01", "DUR-02", "DUR-03", "DUR-04", "DUR-05")),
    }


# ---------------------------------------------------------------- immigration

def eligibility(e: Eligibility, cite: Citations) -> dict:
    return {"status": e.status, "summary": e.summary,
            "checks": [{"test": c.test, "status": c.status, "detail": c.detail, "rule_ids": cite.use(c.rule_ids)}
                       for c in e.checks]}


def requirement_areas(req: Requirements, costs: dict[str, dict], cite: Citations) -> list[dict]:
    return [{
        "key": area.key, "title": area.title,
        "items": [{"id": i.id, "text": i.text, "time": i.time,
                   "cost": costs.get(i.cost_key) if i.cost_key else None,
                   "rule_ids": cite.use(i.rule_ids), "sources": cite.sources(i.rule_ids)}
                  for i in area.items],
    } for area in req.areas]


def timeline(steps: list[Step], total_weeks: Decimal, cite: Citations) -> dict:
    def weeks(x: Decimal) -> str:
        return str(x.quantize(Decimal("0.1"), ROUND_HALF_UP))
    return {
        "total_weeks": weeks(total_weeks),
        "steps": [{"id": s.id, "step": s.step, "party": s.party,
                   "duration": str(s.duration), "unit": s.unit,
                   "start_week": weeks(s.start_week), "end_week": weeks(s.end_week), "skipped": s.skipped,
                   "rule_ids": cite.use(s.rule_ids), "sources": cite.sources(s.rule_ids)} for s in steps],
    }
