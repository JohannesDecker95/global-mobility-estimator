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

    def test_start_during_the_tax_year(self):
        segs = segments(24, start_offset=6)                     # 6 October 2026 to 5 October 2028
        self.assertEqual([(s.label, s.months, s.months_before) for s in segs],
                         [("2026/27", 6, 0), ("2027/28", 12, 6), ("2028/29", 6, 18)])
        self.assertEqual(segs[0].period, "6 October 2026 to 5 April 2027")
        self.assertEqual(segs[-1].period, "6 April 2028 to 5 October 2028")
        self.assertEqual([s.rates_assumed for s in segs], [False, True, True])
        self.assertEqual([s.is_first for s in segs], [True, False, False])

    def test_latest_start(self):
        segs = segments(12, start_offset=11)                    # 6 March 2027 to 5 March 2028
        self.assertEqual([(s.label, s.months) for s in segs], [("2026/27", 1), ("2027/28", 11)])
        self.assertEqual(segs[-1].period, "6 April 2027 to 5 March 2028")


class StartOffsetTests(unittest.TestCase):
    def test_start_must_fall_in_2026_27(self):
        from estimator.engine.inputs import EngineInputError, pack_test_case
        for bad in (-1, 12):
            with self.assertRaises(EngineInputError):
                pack_test_case(start_offset=bad).check()

    def test_housing_kept_home_rule_counts_months_of_the_stay(self):
        """Rz 3008 leaves out the first 12 months of the stay, wherever the tax years fall."""
        from decimal import Decimal
        from estimator.engine.benefits import classify
        from estimator.engine.duration import decide_all
        from estimator.engine.inputs import pack_test_case
        case = pack_test_case(start_offset=6, swiss_home_kept=True)
        segs = segments(case.months, case.start_offset)
        d = decide_all(case)
        housing = [classify(case, seg, d)[0].ahv_in_kind for seg in segs]
        # 6 + 6 months left out, then 6 + 6 months counted at £3,000
        self.assertEqual(housing, [Decimal(0), Decimal(18000), Decimal(18000)])


if __name__ == "__main__":
    unittest.main()
