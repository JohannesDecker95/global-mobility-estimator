"""UK income tax and National Insurance (subtask 7, spec sections 9, 10 and 13)."""
import unittest
from decimal import Decimal as D

from estimator.engine.money import pence
from estimator.engine.uk_tax import (class_1a, closed_form_gross_up, income_tax, nic_employee,
                                     nic_employer, personal_allowance)


class IncomeTaxTests(unittest.TestCase):
    def test_band_edges(self):
        # spec section 13: UKTax at the band edges
        cases = {"12570": "0", "50270": "7540", "100000": "27432", "110000": "33432",
                 "125140": "42516", "150000": "53703"}
        for income, tax in cases.items():
            with self.subTest(income=income):
                self.assertEqual(pence(income_tax(D(income))), D(tax))

    def test_allowance_taper(self):
        self.assertEqual(personal_allowance(D("100000")), D("12570"))
        self.assertEqual(personal_allowance(D("110000")), D("7570"))
        self.assertEqual(personal_allowance(D("125140")), D("0"))
        self.assertEqual(personal_allowance(D("200000")), D("0"))

    def test_zero_and_small_income(self):
        self.assertEqual(income_tax(D("0")), D("0"))
        self.assertEqual(income_tax(D("12000")), D("0"))


class NationalInsuranceTests(unittest.TestCase):
    def test_employee_class_1_full_year(self):
        # 8% of (50,270 - 12,570) + 2% of (60,000 - 50,270)
        self.assertEqual(pence(nic_employee(D("60000"))), D("3210.60"))

    def test_employee_class_1_part_year_uses_monthly_thresholds(self):
        # one month: thresholds 1,047.50 and 4,189.17
        self.assertEqual(pence(nic_employee(D("5000"), months=1)), D("267.55"))

    def test_employer_and_class_1a(self):
        self.assertEqual(pence(nic_employer(D("105000"))), D("15000.00"))
        self.assertEqual(pence(class_1a(D("36000"))), D("5400.00"))

    def test_closed_form_only_above_additional_rate(self):
        self.assertEqual(pence(closed_form_gross_up(D("158478.90"))), D("104579.10"))
        self.assertIsNone(closed_form_gross_up(D("40000")))


if __name__ == "__main__":
    unittest.main()
