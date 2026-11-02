"""Immigration requirements data, eligibility and timeline (subtask 15)."""
import copy
import json
import unittest
from decimal import Decimal

from estimator.engine import requirements as req
from estimator.engine.rules import load_rules


class RequirementsFileTests(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()
        with open(req.DEFAULT_REQUIREMENTS_FILE, encoding="utf-8") as fh:
            self.data = json.load(fh)

    def test_file_is_valid(self):
        self.assertEqual(req.validate(self.data, self.rules), [])

    def test_covers_work_permit_business_visit_and_passport(self):
        keys = [a.key for a in req.load_requirements().areas]
        self.assertEqual(keys, ["work_permit", "business_visit", "passport", "company"])

    def test_placeholders_are_filled_from_rules(self):
        items = {i.id: i for a in req.load_requirements().areas for i in a.items}
        self.assertIn("£52,500", items["WP-1"].text)
        self.assertIn("£1,035", items["WP-4"].text)
        self.assertIn("CHF 145", items["PP-2"].text)
        self.assertEqual(items["BV-1"].time, "Up to 3 working days")

    def test_validation_finds_problems(self):
        bad = copy.deepcopy(self.data)
        bad["areas"][0]["items"][0]["text"] = "Pay {gbp:IMM-WP-01.no_such_field}"
        bad["areas"][0]["items"][1]["rule_ids"] = ["XX-01"]
        bad["timeline"][0]["after"] = ["visa"]
        errors = req.validate(bad, self.rules)
        self.assertEqual(len(errors), 3, errors)


class EligibilityTests(unittest.TestCase):
    def check(self, **kw):
        kw.setdefault("licence_held", True)
        return req.eligibility(**kw)

    def test_high_salary_waives_prior_service(self):
        e = self.check(salary_gbp=Decimal("80000"), months_with_employer=0)
        self.assertEqual(e.status, req.TO_CHECK)    # only the occupation's going rate is left to check

    def test_prior_service_needed_below_the_threshold(self):
        self.assertEqual(self.check(salary_gbp=Decimal("60000"), months_with_employer=11).status, req.NOT_MET)
        self.assertEqual(self.check(salary_gbp=Decimal("60000"), months_with_employer=12).status, req.TO_CHECK)

    def test_salary_below_minimum(self):
        self.assertEqual(self.check(salary_gbp=Decimal("52499.99"), months_with_employer=36).status, req.NOT_MET)

    def test_missing_inputs(self):
        self.assertEqual(self.check(salary_gbp=None, months_with_employer=None).status, req.UNKNOWN)


class TimelineTests(unittest.TestCase):
    def test_licence_then_visa_takes_11_weeks(self):
        steps, total = req.timeline(licence_held=False)
        self.assertEqual(total, Decimal(11))
        visa = next(s for s in steps if s.id == "visa")
        self.assertEqual((visa.start_week, visa.end_week), (Decimal(8), Decimal(11)))

    def test_licence_held_leaves_passport_and_visa(self):
        steps, total = req.timeline(licence_held=True)
        self.assertEqual(total, Decimal(5))
        self.assertTrue(next(s for s in steps if s.id == "licence").skipped)


if __name__ == "__main__":
    unittest.main()
