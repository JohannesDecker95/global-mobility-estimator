"""The full test case and the duration advice (subtask 12, spec sections 11, 13 and 17)."""
import unittest
from dataclasses import replace
from decimal import Decimal as D

from estimator.engine.advice import advise
from estimator.engine.cost_table import BENEFITS, DEDUCTIONS, HOME, HOST, estimate, literal_reading
from estimator.engine.inputs import EngineInputError, Benefit, pack_test_case

CENT = D("0.02")


class TestCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = pack_test_case()
        cls.est = estimate(cls.case)

    def test_totals_with_both_decisions(self):
        self.assertEqual(self.est.totals, [D("273689.09"), D("253432.46")])
        self.assertEqual(self.est.total, D("527121.55"))
        self.assertEqual(round(self.est.multiple, 2), D("1.71"))
        self.assertEqual([round(self.est.year_multiple(i), 2) for i in range(2)], [D("1.77"), D("1.64")])

    def test_literal_reading_comparison(self):
        lit = estimate(literal_reading(self.case))
        self.assertEqual(lit.totals, [D("290403.82"), D("270503.00")])
        self.assertEqual(lit.total, D("560906.82"))

    def test_sections(self):
        s = self.est.subtotals
        self.assertEqual(s[HOME], [D("154545.46"), D("154545.46")])
        self.assertEqual(s[BENEFITS], [D("50545.45"), D("36000.00")])
        self.assertEqual(s[HOST], [D("107210.19"), D("101499.01")])
        self.assertEqual(s[DEDUCTIONS], [D("-38612.01"), D("-38612.01")])

    def test_table_adds_up(self):
        for i, total in enumerate(self.est.totals):
            self.assertEqual(sum(line.amounts[i] for line in self.est.lines), total)

    def test_working(self):
        w = self.est.working[0]
        self.assertEqual(w.rounds, 25)
        self.assertEqual(round(w.ahv_extra_base_chf, 2), D("105874.44"))

    def test_every_line_cites_rules_with_official_links(self):
        from estimator.engine.rules import load_rules
        rules = load_rules()
        for rid in self.est.rule_ids():
            self.assertTrue(rules[rid].urls, rid)

    def test_immigration_for_24_months(self):
        self.assertEqual(self.est.immigration_total, D("8273.50"))
        self.assertEqual(estimate(replace(self.case, months=36)).immigration_total,
                         D("1682") + D("525") + D("1320") + 4 * D("660") + D("1618") + D("1035") * D("3.5") + D("20"))


class SensitivityTests(unittest.TestCase):
    """Spec section 11: changes against the new default."""

    def delta(self, **changes):
        base = estimate(pack_test_case())
        return estimate(pack_test_case(**changes)).total - base.total

    def test_sensitivities(self):
        self.assertLessEqual(abs(self.delta(twr_rule=False) - D("70553.12")), CENT)
        self.assertLessEqual(abs(self.delta(ahv_full_base=False) - D("-26760.18")), CENT)
        self.assertLessEqual(abs(self.delta(swiss_home_kept=True) - D("-6261.25")), CENT)
        self.assertLessEqual(abs(self.delta(pillar2=False) - D("1650.90")), CENT)


class DurationTests(unittest.TestCase):
    def test_25_months_uses_uk_national_insurance(self):
        est = estimate(pack_test_case(months=25))
        self.assertEqual(est.decisions.social_security.system, "UK")
        self.assertEqual(est.year_labels, ["2026/27", "2027/28", "2028/29"])
        ni = next(l for l in est.lines if l.key == "uk_ni")
        self.assertTrue(all(a > 0 for a in ni.amounts))
        self.assertLessEqual(abs(est.all_in - D("649666.44")), D("0.10"))

    def test_advice(self):
        a = advise(pack_test_case())
        self.assertEqual(len(a.rows), 49)
        self.assertEqual(a.planned.months, 24)
        self.assertEqual(a.cheapest.months, 17)
        self.assertEqual(round(a.cheapest.per_month, 2), D("21468.77"))
        self.assertEqual(a.cheapest_from_planned.months, 24)
        self.assertLessEqual(abs(a.next_month_extra - D("114271.41")), D("0.10"))
        self.assertEqual(len(a.thresholds_crossed), 2)


class InputErrorTests(unittest.TestCase):
    def test_bad_inputs_raise_readable_errors(self):
        with self.assertRaisesRegex(EngineInputError, "12 to 60 whole months"):
            estimate(pack_test_case(months=6))
        with self.assertRaisesRegex(EngineInputError, "exchange rate"):
            estimate(pack_test_case(fx_chf_per_gbp=D("0")))
        with self.assertRaisesRegex(EngineInputError, "unknown category"):
            estimate(pack_test_case(benefits=(Benefit("Car", "car", D("1")),)))
        with self.assertRaisesRegex(EngineInputError, "salary_chf"):
            estimate(pack_test_case(salary_chf=D("-1")))


if __name__ == "__main__":
    unittest.main()
