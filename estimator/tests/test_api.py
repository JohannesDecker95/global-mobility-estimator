"""API tests (subtask 16): the full test case through HTTP, and bad input gives 400s.

No database is used, so the tests extend APISimpleTestCase.
"""
from copy import deepcopy
from decimal import Decimal

from rest_framework.test import APISimpleTestCase

from estimator.engine.rules import is_official_url

TEST_CASE = {
    "home_country": "CH", "home_city": "zurich", "host_country": "GB", "host_city": "london",
    "start_date": "2026-04-06", "end_date": "2028-04-05",
    "nationality": "CH", "marital_status": "single", "children": 0,
    "months_with_employer": 36,
    "salary_chf": "150000", "bonus_chf": "20000", "fx_chf_per_gbp": "1.10",
    "sponsor_size": "medium_or_large", "sponsor_licence_held": False,
    "continuing_employment": True, "housing_reasonable": True,
    "swiss_home_kept": False, "art17_exception": False,
    "advice_from": 12, "advice_to": 60,
    "benefits": [
        {"label": "Housing in London", "category": "housing", "amount": "3000",
         "currency": "GBP", "timing": "monthly"},
        {"label": "Relocation allowance", "category": "relocation_allowance", "amount": "5000",
         "currency": "CHF", "timing": "one_off"},
        {"label": "Moving costs (flights, shipping)", "category": "moving_costs", "amount": "6000",
         "currency": "GBP", "timing": "one_off"},
        {"label": "Temporary housing, first 4 weeks", "category": "temporary_housing", "amount": "4000",
         "currency": "GBP", "timing": "one_off"},
    ],
}


def case(**changes):
    data = deepcopy(TEST_CASE)
    data.update(changes)
    return data


class EstimateApiTests(APISimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.response = cls.client_class().post("/api/estimate/", TEST_CASE, format="json")
        cls.body = cls.response.json()

    def test_full_test_case_gives_two_years(self):
        self.assertEqual(self.response.status_code, 200)
        table = self.body["cost_table"]
        self.assertEqual([y["label"] for y in table["years"]], ["2026/27", "2027/28"])
        self.assertEqual(table["totals"], ["273689.09", "253432.46"])
        self.assertEqual(table["total"], "527121.55")
        self.assertEqual(table["multiple"], "1.71")
        self.assertEqual(table["year_multiples"], ["1.77", "1.64"])

    def test_four_sections_add_up(self):
        table = self.body["cost_table"]
        self.assertEqual([s["key"] for s in table["sections"]],
                         ["home_pay", "benefits", "host_tax_and_charges", "deductions"])
        for i, total in enumerate(table["totals"]):
            self.assertEqual(sum(Decimal(s["subtotals"][i]) for s in table["sections"]), Decimal(total))

    def test_every_line_links_to_official_sources(self):
        for section in self.body["cost_table"]["sections"]:
            for line in section["lines"]:
                if section["key"] == "home_pay":          # salary and bonus are the user's inputs
                    self.assertEqual(line["basis"], "input")
                    continue
                self.assertEqual(line["basis"], "rules", line["label"])
                self.assertTrue(line["sources"], line["label"])
                for s in line["sources"]:
                    self.assertTrue(is_official_url(s["url"]), s["url"])
        for rule_id, citation in self.body["rules"].items():
            self.assertTrue(citation["sources"], rule_id)

    def test_every_cited_rule_is_in_the_rules_block(self):
        cited = set()

        def walk(o):
            if isinstance(o, dict):
                cited.update(o.get("rule_ids", []))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk({k: v for k, v in self.body.items() if k != "rules"})
        self.assertTrue(cited)
        self.assertLessEqual(cited, set(self.body["rules"]))

    def test_decisions_and_working(self):
        d = self.body["decisions"]
        self.assertTrue(d["relief"]["applies"])
        self.assertEqual(d["social_security"]["system"], "CH")
        year1 = self.body["working"]["years"][0]
        self.assertEqual(year1["rounds"], len(year1["trace"]))
        self.assertLess(Decimal(year1["last_change"]), Decimal("0.01"))
        self.assertEqual(self.body["working"]["hypothetical_tax"]["total"], "31833.01")

    def test_check_figure_matches_the_official_calculator(self):
        check = self.body["check_figure"]
        self.assertIsNotNone(check)
        self.assertLess(abs(Decimal(check["difference"])), Decimal(1))
        self.assertTrue(is_official_url(check["sources"][0]["url"]))
        self.assertTrue(any("152,400" in step and "153,500" in step for step in check["how_to_check"]))

    def test_settings_and_alternatives_are_explained(self):
        self.assertEqual({s["key"] for s in self.body["settings"]}, {"twr_rule", "ahv_full_base", "pillar2"})
        self.assertTrue(all(s["is_default"] and s["explanation"] for s in self.body["settings"]))
        alts = {a["key"]: a for a in self.body["alternatives"]}
        self.assertEqual(set(alts), {"literal_reading", "without_relief", "salary_only_ahv"})
        literal = alts["literal_reading"]
        self.assertEqual(literal["total"], "560906.82")
        self.assertEqual(literal["difference"], "33785.27")
        self.assertEqual({c["key"] for c in literal["changed"]}, {"twr_rule", "ahv_full_base"})
        housing = next(l for l in literal["lines"] if l["label"] == "Housing in London")
        self.assertEqual(housing["alternative_tag"], "Taxable benefit in kind")
        # the line differences explain the whole difference
        self.assertEqual(sum(Decimal(l["difference"]) for l in literal["lines"]), Decimal(literal["difference"]))

    def test_immigration_costs_and_advice(self):
        imm = self.body["immigration"]
        self.assertEqual(imm["total"], "8273.50")
        self.assertEqual(imm["eligibility"]["status"], "to check")
        self.assertEqual(self.body["all_in"], "535395.05")
        advice = self.body["advice"]
        self.assertEqual(len(advice["rows"]), 49)
        self.assertEqual(advice["cheapest"]["months"], 17)
        self.assertEqual(advice["cheapest"]["per_month"], "21468.77")
        self.assertEqual(advice["planned"]["per_month"], "22308.13")
        self.assertEqual(len(advice["thresholds_crossed"]), 2)

    def test_options_switch_the_method(self):
        r = self.client.post("/api/estimate/", case(options={"twr_rule": False, "ahv_full_base": False}),
                             format="json")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["cost_table"]["total"], "560906.82")
        self.assertFalse(any(s["is_default"] for s in body["settings"] if s["key"] != "pillar2"))
        self.assertIn("default_method", {a["key"] for a in body["alternatives"]})

    def test_25_months_switches_to_uk_national_insurance(self):
        r = self.client.post("/api/estimate/", case(end_date="2028-05-05"), format="json")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["input"]["months"], 25)
        self.assertEqual(body["decisions"]["social_security"]["system"], "UK")
        self.assertFalse(body["decisions"]["relief"]["applies"])
        self.assertEqual(len(body["cost_table"]["years"]), 3)

    def test_start_during_the_tax_year(self):
        r = self.client.post("/api/estimate/", case(start_date="2026-10-06", end_date="2028-10-05"), format="json")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["input"]["months"], 24)
        years = body["cost_table"]["years"]
        self.assertEqual([(y["label"], y["months"]) for y in years], [("2026/27", 6), ("2027/28", 12), ("2028/29", 6)])
        self.assertEqual(years[0]["period"], "6 October 2026 to 5 April 2027")
        self.assertEqual([y["rates_assumed"] for y in years], [False, True, True])
        self.assertEqual(body["cost_table"]["total"], "485730.93")
        self.assertTrue(any("split-year" in w for w in body["warnings"]))
        self.assertTrue(body["decisions"]["relief"]["applies"])

    def test_latest_start(self):
        r = self.client.post("/api/estimate/", case(start_date="2027-03-06", end_date="2028-03-05"), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([y["months"] for y in r.json()["cost_table"]["years"]], [1, 11])

    def test_odd_exchange_rate_gives_a_warning(self):
        r = self.client.post("/api/estimate/", case(fx_chf_per_gbp="5"), format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["warnings"])


class EstimateBadInputTests(APISimpleTestCase):
    def errors(self, data, status=400):
        r = self.client.post("/api/estimate/", data, format="json")
        self.assertEqual(r.status_code, status, r.content)
        return r.json()["errors"]

    def test_missing_salary(self):
        data = case()
        del data["salary_chf"]
        self.assertEqual(self.errors(data)["salary_chf"], ["Base salary is required."])

    def test_salary_with_a_letter(self):
        self.assertIn("for example 150000", self.errors(case(salary_chf="15O000"))["salary_chf"][0])

    def test_negative_bonus(self):
        self.assertIn("0 or more", self.errors(case(bonus_chf=-1))["bonus_chf"][0])

    def test_too_many_decimals(self):
        self.assertIn("at most 2 decimals", self.errors(case(salary_chf="150000.123"))["salary_chf"][0])

    def test_end_before_start(self):
        self.assertIn("after the start date", self.errors(case(end_date="2026-01-05"))["end_date"][0])

    def test_end_not_on_the_fifth(self):
        self.assertIn("5th of a month", self.errors(case(end_date="2028-04-30"))["end_date"][0])

    def test_too_short(self):
        self.assertIn("12 to 60 months", self.errors(case(end_date="2026-10-05"))["end_date"][0])

    def test_start_outside_2026_27_or_not_on_the_6th(self):
        for start, end in (("2027-04-06", "2029-04-05"), ("2026-03-06", "2028-03-05"), ("2026-10-07", "2028-10-05")):
            errors = self.errors(case(start_date=start, end_date=end))
            self.assertIn("6th of a month from 6 April 2026 to 6 March 2027", errors["start_date"][0], start)

    def test_unsupported_choices(self):
        errors = self.errors(case(nationality="DE", host_city="edinburgh", marital_status="married", children=1))
        self.assertEqual(set(errors), {"nationality", "host_city", "marital_status", "children"})
        self.assertTrue(all("not supported yet" in m[0] for m in errors.values()))

    def test_bad_benefit(self):
        bad = {"label": "", "category": "car", "amount": "-5", "currency": "EUR", "timing": "weekly"}
        errors = self.errors(case(benefits=[TEST_CASE["benefits"][0], bad]))
        self.assertEqual(set(errors), {"benefits.1.label", "benefits.1.category", "benefits.1.amount",
                                       "benefits.1.currency", "benefits.1.timing"})

    def test_bad_option(self):
        self.assertIn("true or false", self.errors(case(options={"twr_rule": "maybe"}))["options.twr_rule"][0])

    def test_not_json(self):
        r = self.client.post("/api/estimate/", "{not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json(), {"errors": {"request": ["The request body is not valid JSON."]}})

    def test_wrong_method(self):
        r = self.client.get("/api/estimate/")
        self.assertEqual(r.status_code, 405)
        self.assertIn("request", r.json()["errors"])


class ImmigrationApiTests(APISimpleTestCase):
    URL = "/api/immigration/"

    def test_test_case(self):
        r = self.client.get(self.URL, {"nationality": "CH", "host": "GB", "sponsor_size": "medium_or_large",
                                       "months": 24, "salary_gbp": "136363.64", "months_with_employer": 36})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual([a["key"] for a in body["areas"]], ["work_permit", "business_visit", "passport", "company"])
        self.assertEqual(body["costs"]["total"], "8273.50")
        self.assertEqual(body["timeline"]["total_weeks"], "11.0")
        self.assertEqual(body["eligibility"]["status"], "to check")
        for area in body["areas"]:
            for item in area["items"]:
                self.assertNotIn("{", item["text"])
                self.assertTrue(item["sources"], item["id"])
                for s in item["sources"]:
                    self.assertTrue(is_official_url(s["url"]), s["url"])

    def test_small_sponsor_with_licence(self):
        r = self.client.get(self.URL, {"nationality": "CH", "host": "GB", "sponsor_size": "small",
                                       "months": 24, "sponsor_licence_held": "true"})
        body = r.json()
        self.assertEqual(body["costs"]["total"], "4911.50")       # 0 + 525 + 960 + 819 + 2,587.50 + 20
        self.assertEqual(body["timeline"]["total_weeks"], "5.0")  # passport 2 weeks, then the visa 3
        self.assertEqual(body["eligibility"]["status"], "not checked")

    def test_low_salary_is_not_eligible(self):
        r = self.client.get(self.URL, {"nationality": "CH", "host": "GB", "salary_gbp": "40000",
                                       "months_with_employer": 6})
        self.assertEqual(r.json()["eligibility"]["status"], "not met")

    def test_bad_query(self):
        r = self.client.get(self.URL, {"nationality": "DE", "host": "GB", "months": "abc"})
        self.assertEqual(r.status_code, 400)
        errors = r.json()["errors"]
        self.assertIn("not supported yet", errors["nationality"][0])
        self.assertIn("whole number", errors["months"][0])

    def test_missing_nationality(self):
        r = self.client.get(self.URL, {"host": "GB"})
        self.assertEqual(r.json()["errors"]["nationality"], ["Nationality is required."])
