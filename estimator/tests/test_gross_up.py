"""Tax on tax (subtask 11, spec sections 9, 10 and 16)."""
import unittest
from decimal import Decimal as D

from estimator.engine.gross_up import gross_up, solve_swiss, solve_uk
from estimator.engine.money import pence
from estimator.engine.uk_tax import closed_form_gross_up, income_tax, nic_employee


class BriefGrossUpTests(unittest.TestCase):
    def test_year_1_fixture(self):
        # spec section 9: I = £158,478.90 gives T = £104,579.10 in 24 rounds
        t, trace = gross_up(D("158478.90"))
        self.assertEqual(pence(t), D("104579.10"))
        self.assertEqual(trace.count, 24)
        self.assertEqual([pence(v) for _, v in trace.rounds[:3]],
                         [D("57518.51"), D("83401.83"), D("95049.33")])
        self.assertLess(abs(income_tax(D("158478.90") + t) - t), D("0.01"))
        self.assertEqual(pence(t), pence(closed_form_gross_up(D("158478.90"))))

    def test_year_2_and_low_income(self):
        self.assertEqual(pence(gross_up(D("151933.45"))[0]), D("99223.73"))
        # in the allowance taper the marginal rate is 60%: still converges
        t, _ = gross_up(D("90000"))
        self.assertLess(abs(income_tax(D("90000") + t) - t), D("0.01"))


class SwissBranchTests(unittest.TestCase):
    def test_full_ahv_base_test_case_year_1(self):
        b = solve_swiss(home_pay=D("170000") / D("1.10"), hypo_tax=D("31833.01") / D("1.10"),
                        uk_base=D("115933.45") + D("4545.45"), ahv_cash=D("5000") / D("1.10"),
                        ahv_in_kind=D("40000"), months=12, fx=D("1.10"), full_base=True)
        self.assertEqual(pence(b.tax), D("77661.92"))
        self.assertEqual(pence(b.ahv_extra_base * D("1.10")), D("105874.44"))
        self.assertEqual(pence(b.extra_employee_ss + b.extra_employer_ss), D("10202.45"))
        # the extra employee share is in UK taxable pay, and the fixed point holds
        self.assertLess(abs(income_tax(b.taxable_pay + b.tax) - b.tax), D("0.01"))

    def test_salary_only_base_equals_the_brief_formula(self):
        b = solve_swiss(home_pay=D("154545.45"), hypo_tax=D("28939.10"), uk_base=D("158478.90"),
                        ahv_cash=D("4545.45"), ahv_in_kind=D("40000"), months=12, fx=D("1.10"),
                        full_base=False)
        self.assertEqual(pence(b.tax), D("104579.10"))
        self.assertEqual(b.ahv_extra_base, 0)


class UKBranchTests(unittest.TestCase):
    def test_tax_and_employee_ni_solved_together(self):
        cash, kind = D("120000"), D("36000")
        b = solve_uk(cash=cash, in_kind=kind, months=12)
        g = b.tax + b.employee_ni
        self.assertLess(abs(income_tax(cash + kind + g) - b.tax), D("0.01"))
        self.assertLess(abs(nic_employee(cash + g) - b.employee_ni), D("0.01"))


if __name__ == "__main__":
    unittest.main()
