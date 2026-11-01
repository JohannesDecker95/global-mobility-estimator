"""UK tags and AHV treatment of benefits (subtask 10, spec sections 8 and 16)."""
import unittest
from decimal import Decimal as D

from estimator.engine.benefits import classify
from estimator.engine.duration import decide_all, segments
from estimator.engine.inputs import OTHER_CASH, OTHER_IN_KIND, ONE_OFF, Benefit, pack_test_case
from estimator.engine.money import pence


def year(case, k=0):
    seg = segments(case.months)[k]
    return classify(case, seg, decide_all(case))


def taxable(lines):
    return pence(sum((l.uk_taxable for l in lines), D(0)))


class LiteralReadingTests(unittest.TestCase):
    """No relief: spec section 8 table."""

    def setUp(self):
        self.case = pack_test_case(twr_rule=False)

    def test_tags(self):
        tags = [l.uk_tag for l in year(self.case)]
        self.assertEqual(tags, ["Taxable benefit in kind", "Taxable cash", "Not taxable: relocation exemption",
                                "£2,000.00 not taxable (relocation exemption), £2,000.00 taxable benefit in kind"])

    def test_taxable_amounts(self):
        self.assertEqual(taxable(year(self.case, 0)), D("42545.45"))
        self.assertEqual(taxable(year(self.case, 1)), D("36000.00"))


class ReliefTests(unittest.TestCase):
    """24-month relief applied (spec section 17)."""

    def test_only_the_cash_allowance_is_taxable(self):
        case = pack_test_case()
        lines = year(case)
        self.assertEqual(taxable(lines), D("4545.45"))
        self.assertEqual(lines[0].uk_tag, "Not taxable: temporary-workplace relief")
        self.assertEqual(lines[3].uk_tag, "Not taxable: temporary-workplace relief")
        self.assertEqual(taxable(year(case, 1)), D("0.00"))


class AhvTreatmentTests(unittest.TestCase):
    def ahv(self, case, k=0):
        lines = year(case, k)
        return (pence(sum((l.ahv_cash for l in lines), D(0))),
                pence(sum((l.ahv_in_kind for l in lines), D(0))))

    def test_test_case(self):
        # cash: relocation allowance; in kind: housing + temporary housing; moving costs excluded
        self.assertEqual(self.ahv(pack_test_case()), (D("4545.45"), D("40000.00")))

    def test_swiss_home_kept_excludes_12_months_of_housing(self):
        case = pack_test_case(swiss_home_kept=True)
        self.assertEqual(self.ahv(case, 0), (D("4545.45"), D("0.00")))
        self.assertEqual(self.ahv(case, 1), (D("0.00"), D("36000.00")))


class OtherCategoriesTests(unittest.TestCase):
    def test_other_cash_and_in_kind(self):
        case = pack_test_case(benefits=(
            Benefit("Cost-of-living allowance", OTHER_CASH, D("1000"), "GBP", ONE_OFF),
            Benefit("Language course", OTHER_IN_KIND, D("2200"), "CHF", ONE_OFF),
        ))
        cash, kind = year(case)
        self.assertEqual((cash.uk_tag, cash.uk_cash, cash.ahv_cash), ("Taxable cash", D("1000"), D("1000")))
        self.assertEqual(kind.uk_tag, "Taxable benefit in kind")
        self.assertEqual(pence(kind.uk_in_kind), D("2000.00"))
        self.assertEqual(pence(kind.ahv_in_kind), D("2000.00"))


if __name__ == "__main__":
    unittest.main()
