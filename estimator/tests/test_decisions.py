"""Social security and duration decisions (subtask 9, spec sections 7 and 17)."""
import unittest

from estimator.engine.duration import decide_all, segments
from estimator.engine.inputs import pack_test_case


class SocialSecurityTests(unittest.TestCase):
    def system(self, **changes):
        return decide_all(pack_test_case(**changes)).social_security.system

    def test_test_case_keeps_swiss_social_security(self):
        self.assertEqual(self.system(), "CH")

    def test_over_24_months_moves_to_uk_national_insurance(self):
        self.assertEqual(self.system(months=25), "UK")

    def test_article_17_exception_keeps_swiss_cover(self):
        self.assertEqual(self.system(months=36, art17_exception=True), "CH")

    def test_new_uk_employment_or_no_prior_insurance_fails_article_14(self):
        self.assertEqual(self.system(continuing_employment=False), "UK")
        self.assertEqual(self.system(months_with_employer=0), "UK")


class ReliefTests(unittest.TestCase):
    def relief(self, **changes):
        return decide_all(pack_test_case(**changes)).relief

    def test_exactly_24_months_qualifies(self):
        self.assertTrue(self.relief())

    def test_relief_conditions(self):
        self.assertFalse(self.relief(months=25))
        self.assertFalse(self.relief(continuing_employment=False))
        self.assertFalse(self.relief(housing_reasonable=False))
        self.assertFalse(self.relief(twr_rule=False))


class SegmentTests(unittest.TestCase):
    def test_tax_years(self):
        self.assertEqual([(s.label, s.months) for s in segments(24)], [("2026/27", 12), ("2027/28", 12)])
        self.assertEqual([(s.label, s.months, s.months_before) for s in segments(17)],
                         [("2026/27", 12, 0), ("2027/28", 5, 12)])


if __name__ == "__main__":
    unittest.main()
