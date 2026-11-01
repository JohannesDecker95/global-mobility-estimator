"""Tests for the rules data file and its loader (subtask 6, checks 3 and 9)."""

import copy
import json
import unittest
from decimal import Decimal

from estimator.engine.rules import (
    DEFAULT_RULES_FILE,
    RuleSet,
    RulesError,
    is_official_url,
    load_rules,
    validate,
)


def raw():
    with open(DEFAULT_RULES_FILE, encoding="utf-8") as fh:
        return json.load(fh, parse_float=Decimal, parse_int=Decimal)


class RulesFileTests(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()

    def test_file_is_valid(self):
        self.assertEqual(validate(raw()), [])

    def test_every_rule_has_an_official_link(self):
        for rule in self.rules:
            with self.subTest(rule=rule.rule_id):
                self.assertTrue(rule.urls)
                for url in rule.urls:
                    self.assertTrue(is_official_url(url), url)

    def test_register_is_complete(self):
        expected = {
            "UK-IT-01",
            "UK-IT-02",
            "UK-IT-03",
            "UK-IT-04",
            "UK-IT-05",
            "UK-TE-01",
            "UK-TE-02",
            "UK-PAYE-01",
            "UK-DTA-01",
            "UK-NI-01",
            "UK-NI-02",
            "UK-NI-03",
            "UK-NI-04",
            "UK-AL-01",
            "SS-CONV-01",
            "SS-CONV-02",
            "SS-CONV-03",
            "SS-CONV-04",
            "SS-CH-01",
            "SS-UK-01",
            "CH-SS-01",
            "CH-SS-02",
            "IMM-WP-01",
            "IMM-WP-02",
            "IMM-WP-03",
            "IMM-WP-04",
            "IMM-BV-01",
            "IMM-BV-02",
            "IMM-PP-01",
            "IMM-PP-02",
            "IMM-SP-01",
            "IMM-SP-02",
            "IMM-SP-03",
            "IMM-SP-04",
            "IMM-RTW-01",
        }
        expected |= {f"UK-BEN-0{i}" for i in range(1, 9)}
        expected |= {f"CH-AHV-0{i}" for i in range(1, 7)}
        expected |= {f"CH-TAX-{i:02d}" for i in range(1, 11)}
        expected |= {f"DUR-0{i}" for i in range(1, 7)}
        self.assertEqual({r.rule_id for r in self.rules}, expected)

    def test_every_number_is_decimal(self):
        self.assertIsInstance(self.rules["UK-IT-03"]["rate"], Decimal)
        self.assertEqual(self.rules["CH-SS-01"]["employee_rate"], Decimal("0.053"))
        self.assertIsInstance(self.rules["UK-IT-01"]["personal_allowance"], Decimal)
        self.assertIsInstance(self.rules["CH-TAX-01"]["brackets"][1][0], Decimal)

    def test_key_figures_match_the_spec(self):
        r = self.rules
        self.assertEqual(r["UK-IT-01"]["personal_allowance"], 12570)
        self.assertEqual(r["UK-IT-04"]["upper_limit"], 125140)
        self.assertEqual(r["UK-NI-02"]["rate"], Decimal("0.15"))
        self.assertEqual(r["CH-SS-02"]["ceiling"], 148200)
        self.assertEqual(r["CH-TAX-06"]["multiplier"], Decimal("0.95"))
        self.assertEqual(r["CH-TAX-07"]["multiplier"], Decimal("1.19"))
        self.assertEqual(r["DUR-01"]["max_months"], 24)
        self.assertEqual(r["DUR-03"]["max_months"], 72)
        self.assertEqual(r["IMM-SP-03"]["large_first_12_months"], 1320)

    def test_federal_tariff_is_ordered_and_continuous(self):
        brackets = self.rules["CH-TAX-01"]["brackets"]
        thresholds = [b[0] for b in brackets]
        self.assertEqual(thresholds, sorted(thresholds))
        # tax at each threshold = tax at the previous one + the per-100 rate over the gap;
        # the published tariff rounds each step to 5 Rappen, so allow CHF 0.05
        for (t0, a0, r0), (t1, a1, _) in zip(brackets[1:], brackets[2:]):
            with self.subTest(threshold=t1):
                self.assertLessEqual(
                    abs(a0 + (t1 - t0) / 100 * r0 - a1), Decimal("0.05")
                )

    def test_zurich_tariff_reaches_the_top_bracket(self):
        value = self.rules["CH-TAX-04"].value
        self.assertEqual(
            sum(width for width, _ in value["brackets"]), value["top_from"]
        )

    def test_data_reproduces_the_estv_check(self):
        # The tariffs in the file give the hypothetical tax the ESTV calculator confirmed (CH-TAX-10).
        r = self.rules
        check = r["CH-TAX-10"]
        fed_brackets = r["CH-TAX-01"]["brackets"]
        income = check["federal_taxable"]
        threshold, at, per100 = [b for b in fed_brackets if b[0] <= income][-1]
        federal = at + (income - threshold) / 100 * per100
        self.assertEqual(federal, Decimal("7460.55"))

        rest, simple = check["cantonal_taxable"], Decimal(0)
        for width, rate in r["CH-TAX-04"]["brackets"]:
            part = min(rest, width)
            simple += part * rate
            rest -= part
        self.assertEqual(simple, Decimal("11389"))
        cantonal = simple * r["CH-TAX-06"]["multiplier"]
        communal = simple * r["CH-TAX-07"]["multiplier"]
        self.assertEqual(round(cantonal), check["cantonal"])
        self.assertEqual(round(communal), check["communal"])
        self.assertEqual(round(federal), check["federal"])
        # the calculator adds its rounded parts
        parts = (
            round(federal)
            + round(cantonal)
            + round(communal)
            + r["CH-TAX-08"]["amount"]
        )
        self.assertEqual(parts, check["total"])

    def test_citations_carry_links(self):
        cites = self.rules.citations(["UK-IT-01", "UK-IT-02", "UK-IT-01"])
        self.assertEqual([c["rule_id"] for c in cites], ["UK-IT-01", "UK-IT-02"])
        self.assertTrue(cites[0]["sources"][0]["url"].startswith("https://www.gov.uk/"))


class ValidationTests(unittest.TestCase):
    def test_unknown_rule_gives_a_clear_error(self):
        with self.assertRaisesRegex(RulesError, "Unknown rule ID 'UK-XX-99'"):
            load_rules()["UK-XX-99"]

    def test_unknown_value_field_gives_a_clear_error(self):
        with self.assertRaisesRegex(RulesError, "UK-IT-01 has no value 'rate'"):
            load_rules()["UK-IT-01"]["rate"]

    def test_unofficial_source_is_rejected(self):
        data = copy.deepcopy(raw())
        data["sources"]["gov-income-tax-rates"]["url"] = "https://example.com/tax"
        with self.assertRaisesRegex(RulesError, "not an official https page"):
            RuleSet(data)

    def test_missing_source_and_duplicate_id_are_rejected(self):
        data = copy.deepcopy(raw())
        data["rules"][0]["sources"] = ["no-such-source"]
        data["rules"].append(copy.deepcopy(data["rules"][1]))
        errors = validate(data)
        self.assertTrue(any("unknown source 'no-such-source'" in e for e in errors))
        self.assertTrue(any("appears twice" in e for e in errors))

    def test_official_hosts(self):
        self.assertTrue(is_official_url("https://www.gov.uk/income-tax-rates"))
        self.assertTrue(
            is_official_url("https://sozialversicherungen.admin.ch/de/d/6944")
        )
        self.assertFalse(is_official_url("http://www.gov.uk/income-tax-rates"))
        self.assertFalse(is_official_url("https://gov.uk.example.com/"))


if __name__ == "__main__":
    unittest.main()
