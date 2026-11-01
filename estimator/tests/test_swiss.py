"""Hypothetical Swiss tax and social security (subtasks 8 and 9, spec sections 5, 6 and 13)."""
import unittest
from decimal import Decimal as D

from estimator.engine.money import pence
from estimator.engine.rules import load_rules
from estimator.engine.swiss_social import employee_contributions, employer_contributions
from estimator.engine.swiss_tax import federal_tax, hypothetical_tax, zurich_basic_tax


class SwissSocialSecurityTests(unittest.TestCase):
    def test_contributions_on_170000(self):
        # 5.3% of 170,000 + 1.1% of the 148,200 ceiling
        self.assertEqual(employee_contributions(D("170000")), D("10640.2000"))
        self.assertEqual(employer_contributions(D("170000")), employee_contributions(D("170000")))

    def test_below_the_alv_ceiling(self):
        self.assertEqual(employee_contributions(D("100000")), D("6400.000"))

    def test_gbp_base_and_part_year(self):
        # half a year in GBP at CHF 1.10: same as CHF 85,000 for 6 months, converted
        gbp = employee_contributions(D("85000") / D("1.10"), months=6, chf_per_unit=D("1.10"))
        chf = employee_contributions(D("85000"), months=6)
        self.assertEqual(pence(gbp * D("1.10")), pence(chf))


class SwissTaxTests(unittest.TestCase):
    def test_federal_tax(self):
        self.assertEqual(federal_tax(D("153559.80")), D("7460.55"))
        self.assertEqual(federal_tax(D("15000")), D("0"))          # below the first bracket
        self.assertEqual(federal_tax(D("900000")), D("103500.00"))  # flat 11.5%

    def test_zurich_basic_tax(self):
        self.assertEqual(zurich_basic_tax(D("152459.80")), D("11389.00"))

    def test_hypothetical_tax_test_case(self):
        h = hypothetical_tax(D("170000"))
        self.assertEqual(h.social_security, D("10640.2000"))
        self.assertEqual(pence(h.cantonal), D("10819.55"))
        self.assertEqual(pence(h.communal), D("13552.91"))
        self.assertEqual(pence(h.total), D("31833.01"))

    def test_without_pillar_2(self):
        # spec section 5: the insurance allowances rise to CHF 2,700 and 4,350
        self.assertEqual(pence(hypothetical_tax(D("170000"), pillar2=False).total), D("31404.45"))

    def test_regierungsrat_burden_table(self):
        # CH-TAX-09: rebuilt at 98% with church tax, Personalsteuer and federal tax, within CHF 5
        r = load_rules()
        check = r["CH-TAX-09"]
        multiplier = check["cantonal_multiplier"] + r["CH-TAX-07"]["multiplier"] + check["church_multiplier"]
        for income, official in check["points"]:
            with self.subTest(income=income):
                ours = (zurich_basic_tax(income) * multiplier + r["CH-TAX-08"]["amount"]
                        + federal_tax(income))
                self.assertLessEqual(abs(ours - official), check["tolerance"])


if __name__ == "__main__":
    unittest.main()
