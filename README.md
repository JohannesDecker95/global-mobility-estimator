# Global Mobility Estimator

## Requirements

Python 3.12 or later (Django 6.1 does not run on older versions). Check with
`python3 --version`.

## Rules data

Every rate, threshold and fee the estimator uses lives in one file,
`estimator/rules/rules_2026.json`, never in the code. Each rule has an ID (for example
`UK-IT-01`), its value and the official page it comes from. The engine reads the rules
through `estimator/engine/rules.py` and can return the source links with every figure.

When rates change, edit or add a rules file; the loader refuses a file with a missing
field, an unknown source or a link that is not an official https page.

## Calculation engine

`estimator/engine/` is plain Python with no Django imports, one module per step:

| Module | What it does |
|---|---|
| `inputs.py` | The case (salary, bonus, months, benefits, options) and input checks |
| `duration.py`, `social_security.py` | The 24-month decisions: temporary-workplace relief and which social security system applies |
| `benefits.py` | Tags each benefit for UK tax and Swiss AHV |
| `uk_tax.py`, `swiss_tax.py`, `swiss_social.py` | UK income tax and NI, hypothetical Swiss tax, Swiss social security |
| `gross_up.py` | Tax on tax, by iteration |
| `cost_table.py` | The four-section cost table per UK tax year, totals and multiple of home pay |
| `immigration.py`, `advice.py` | Immigration costs and the cheapest length of stay |

Amounts use `Decimal`. Each line is rounded to the penny before it is added, so the table
always adds up.

## Tests

```bash
python manage.py test estimator
```
