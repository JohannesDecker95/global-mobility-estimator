"""Method switches and alternative calculations (point 2 of 1 November 2026)."""
import unittest
from decimal import Decimal

from estimator.engine.alternatives import SWITCHES, alternatives, switch_states
from estimator.engine.cost_table import estimate
from estimator.engine.inputs import pack_test_case
from estimator.engine.rules import load_rules


class AlternativesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = pack_test_case()
        cls.main = estimate(cls.case)
        cls.alts = {a.definition.key: a for a in alternatives(cls.case, cls.main)}

    def test_default_case_shows_three_alternatives(self):
        self.assertEqual(set(self.alts), {"literal_reading", "without_relief", "salary_only_ahv"})

    def test_literal_reading(self):
        a = self.alts["literal_reading"]
        self.assertEqual(a.result.total, Decimal("560906.82"))
        self.assertEqual(a.difference, Decimal("33785.27"))
        self.assertEqual(sum(l.difference for l in a.lines), a.difference)
        self.assertEqual(sum(a.year_differences), a.difference)

    def test_single_switches(self):
        self.assertEqual(self.alts["without_relief"].difference, Decimal("70553.12"))
        self.assertEqual(self.alts["salary_only_ahv"].difference, Decimal("-26760.19"))
        self.assertEqual([s.switch.key for s in self.alts["without_relief"].changed], ["twr_rule"])

    def test_tag_changes_are_listed(self):
        housing = next(l for l in self.alts["without_relief"].lines if l.key == "benefit_0")
        self.assertEqual(housing.difference, 0)
        self.assertEqual(housing.alternative_tag, "Taxable benefit in kind")

    def test_literal_case_offers_the_default_method(self):
        case = pack_test_case(twr_rule=False, ahv_full_base=False)
        keys = {a.definition.key for a in alternatives(case)}
        self.assertEqual(keys, {"default_method", "without_relief", "salary_only_ahv"})

    def test_switches_are_explained_and_cite_known_rules(self):
        rules = load_rules()
        for state in switch_states(self.case):
            self.assertTrue(state.is_default)
            self.assertTrue(state.explanation)
        for s in SWITCHES:
            self.assertTrue(s.on and s.off)
            for rid in s.rule_ids:
                self.assertIn(rid, rules)


if __name__ == "__main__":
    unittest.main()
