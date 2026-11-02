"""The two API endpoints (subtasks 14 and 15).

POST /api/estimate/     the cost table, decisions, working, alternatives, immigration
                        costs and duration advice for one assignment
GET  /api/immigration/  requirements, eligibility, timeline and fees for the immigration tab

Both validate first and answer bad input with HTTP 400 and a message per field. The
engine checks the same limits again; if it still refuses an input, that is a 400 too.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from rest_framework.response import Response
from rest_framework.views import APIView

from ..engine import advice as advice_engine
from ..engine import alternatives as alt_engine
from ..engine import immigration as imm_engine
from ..engine import requirements as req_engine
from ..engine.cost_table import estimate
from ..engine.gross_up import GrossUpError
from ..engine.inputs import Case, EngineInputError
from ..engine.rules import load_rules
from . import present
from .errors import error_response
from .serializers import SPONSOR_SIZES, EstimateSerializer, ImmigrationQuerySerializer

FX_WARN_LOW, FX_WARN_HIGH = Decimal("0.50"), Decimal("3.00")


class EstimateView(APIView):
    def post(self, request):
        s = EstimateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        try:
            case = s.to_case()
            body = build_estimate(case, data["advice_from"], data["advice_to"])
        except EngineInputError as exc:
            return error_response({"input": [str(exc)]})
        except GrossUpError:
            return error_response({"input": ["The tax-on-tax calculation did not settle for these inputs. "
                                             "Check the amounts for typing errors."]}, 422)
        body["input"] = {**s.data, "months": data["months"]}
        if data["start_offset"]:
            body["warnings"].append(
                "The stay starts during a UK tax year, so the first and last tax years are part years. Each "
                "keeps the full personal allowance and tax bands (split-year treatment), which lowers the "
                "UK tax compared with a stay starting on 6 April.")
        if not FX_WARN_LOW <= data["fx_chf_per_gbp"] <= FX_WARN_HIGH:
            body["warnings"].append(f"The exchange rate {data['fx_chf_per_gbp']} CHF per £1 is outside "
                                    f"{FX_WARN_LOW} to {FX_WARN_HIGH}; please check it.")
        return Response(body)


def build_estimate(case: Case, advice_from: int, advice_to: int) -> dict:
    rules = load_rules()
    cite = present.Citations(rules)
    main = estimate(case, rules)
    alts = alt_engine.alternatives(case, main, rules)
    adv = advice_engine.advise(case, advice_from, advice_to, rules)
    salary_gbp = case.salary_chf / case.fx_chf_per_gbp
    elig = req_engine.eligibility(salary_gbp=salary_gbp, months_with_employer=case.months_with_employer,
                                  licence_held=case.sponsor_licence_held, rules=rules)
    body = {
        "warnings": [],
        "decisions": present.decisions(main, cite),
        "settings": present.settings(alt_engine.switch_states(case), cite),
        "cost_table": present.cost_table(main, cite),
        "working": {
            "hypothetical_tax": present.hypothetical_tax(main.hypothetical, cite),
            "years": present.working(main, cite),
        },
        "check_figure": present.check_figure(main.hypothetical, rules, cite),
        "alternatives": present.alternatives(alts, main, cite),
        "immigration": {**present.immigration_costs(main, cite),
                        "eligibility": present.eligibility(elig, cite)},
        "all_in": present.m(main.all_in),
        "per_month": present.m(main.per_month),
        "advice": present.advice(adv, min(advice_from, case.months), max(advice_to, case.months), cite),
        "assumptions": main.assumptions,
    }
    body["rules"] = cite.block()
    return body


class ImmigrationView(APIView):
    def get(self, request):
        s = ImmigrationQuerySerializer(data=request.query_params)
        s.is_valid(raise_exception=True)
        q = s.validated_data
        rules = load_rules()
        cite = present.Citations(rules)
        req = req_engine.load_requirements()
        case = replace(Case(), months=q["months"], sponsor_large=q["sponsor_size"] == "medium_or_large",
                       sponsor_licence_held=q["sponsor_licence_held"])
        cost_items = imm_engine.costs(case, rules)
        costs = {c.key: {"label": c.label, "amount": present.m(c.amount), "paid_by": c.paid_by}
                 for c in cost_items}
        steps, total_weeks = req_engine.timeline(licence_held=q["sponsor_licence_held"], requirements=req,
                                                 rules=rules)
        elig = req_engine.eligibility(salary_gbp=q["salary_gbp"], months_with_employer=q["months_with_employer"],
                                      licence_held=q["sponsor_licence_held"], rules=rules)
        total = sum((c.amount for c in cost_items), Decimal(0))
        body = {
            "input": {**s.data, "sponsor_size_label": SPONSOR_SIZES[q["sponsor_size"]]},
            "route": {"title": req.title, "summary": req.summary,
                      "rule_ids": cite.use(req.route_rule_ids), "sources": cite.sources(req.route_rule_ids)},
            "eligibility": present.eligibility(elig, cite),
            "areas": present.requirement_areas(req, costs, cite),
            "timeline": present.timeline(steps, total_weeks, cite),
            "costs": {
                "items": [{"key": c.key, "label": c.label, "amount": present.m(c.amount), "paid_by": c.paid_by,
                           "rule_ids": cite.use(c.rule_ids), "sources": cite.sources(c.rule_ids)}
                          for c in cost_items],
                "total": present.m(total),
                "optional_extras": [
                    {"label": "Faster sponsor licence decision", "amount": present.m(rules["IMM-SP-01"]["priority_fee"]),
                     "currency": "GBP", "rule_ids": cite.use(("IMM-SP-01",))},
                    {"label": "Faster visa decision (priority)", "amount": present.m(rules["IMM-WP-03"]["priority_fee"]),
                     "currency": "GBP", "rule_ids": cite.use(("IMM-WP-03",))},
                    {"label": "Faster visa decision (super priority)",
                     "amount": present.m(rules["IMM-WP-03"]["super_priority_fee"]),
                     "currency": "GBP", "rule_ids": cite.use(("IMM-WP-03",))},
                    {"label": "Passport renewal, if needed", "amount": present.m(rules["IMM-PP-02"]["fee"]),
                     "currency": "CHF", "rule_ids": cite.use(("IMM-PP-02",))},
                ],
            },
        }
        cite.use(req.rule_ids())
        body["rules"] = cite.block()
        return Response(body)
