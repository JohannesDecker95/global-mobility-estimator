# Global Mobility Estimator

Estimates what a Zurich to London assignment costs the employer under tax equalisation,
and what the employee and the employer need for UK immigration. Every rate, fee and
requirement links to the official page it comes from.

## Requirements

Python 3.12 or later (Django 6.1 does not run on older versions). Check with
`python3 --version`.

## Install and run

```bash
git clone https://github.com/JohannesDecker95/global-mobility-estimator.git
cd global-mobility-estimator
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver
```

The API then runs at http://127.0.0.1:8000/api/. Nothing else is needed for local use:
there is no database to set up, and without `DJANGO_SECRET_KEY` a random key is made at
each start. For a shared server, set the variables listed in `.env.example` in the
environment (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`).

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
| `alternatives.py` | The method switches explained, and the alternative calculations with line-by-line differences |
| `requirements.py` | Immigration requirements, eligibility and timeline, from `rules/requirements_2026.json` |

Amounts use `Decimal`. Each line is rounded to the penny before it is added, so the table
always adds up.

## API

Both endpoints answer in JSON. Bad input gets HTTP 400 with one message per field:
`{"errors": {"salary_chf": ["Base salary is required."]}}`. Money is sent as strings with
two decimals, and every figure carries rule IDs that resolve to official links in the
response's `rules` block.

**`POST /api/estimate/`** takes the assignment and returns the cost table per UK tax year,
the 24-month decisions with their reasons, the gross-up working, the method settings and
alternative calculations, immigration costs and the duration advice. The test case:

```bash
curl -X POST http://127.0.0.1:8000/api/estimate/ -H "Content-Type: application/json" -d '{
  "start_date": "2026-04-06", "end_date": "2028-04-05", "months_with_employer": 36,
  "salary_chf": "150000", "bonus_chf": "20000", "fx_chf_per_gbp": "1.10",
  "benefits": [
    {"label": "Housing in London", "category": "housing", "amount": "3000", "currency": "GBP", "timing": "monthly"},
    {"label": "Relocation allowance", "category": "relocation_allowance", "amount": "5000", "currency": "CHF", "timing": "one_off"},
    {"label": "Moving costs (flights, shipping)", "category": "moving_costs", "amount": "6000", "currency": "GBP", "timing": "one_off"},
    {"label": "Temporary housing, first 4 weeks", "category": "temporary_housing", "amount": "4000", "currency": "GBP", "timing": "one_off"}
  ]
}'
```

Optional fields have defaults: countries and cities (`CH`, `zurich`, `GB`, `london`),
`nationality`, `marital_status`, `children`, `sponsor_size`, the yes/no facts of spec
section 4, `advice_from`/`advice_to`, and `options` with the method switches `twr_rule`,
`ahv_full_base` and `pillar2`. A stay starts on the 6th of a month from 6 April 2026 to
6 March 2027 (inside UK tax year 2026/27, which the rules cover) and ends on the 5th of a
month, 12 to 60 months later. Later tax years use the 2026/27 rates; the response marks them.

**`GET /api/immigration/?nationality=CH&host=GB`** returns the requirements for the work
permit, the business visit, the passport and the employer, with eligibility, timeline and
fees. Optional: `sponsor_size`, `months`, `sponsor_licence_held`, `salary_gbp`,
`months_with_employer`.

## Tests

```bash
python manage.py test estimator
```
