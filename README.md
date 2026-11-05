# Global Mobility Estimator

Estimates what a Zurich to London assignment costs the employer under tax equalisation,
and what the employee and the employer need for UK immigration. Every rate, fee and
requirement links to the official page it comes from.

## Walkthrough video

[▶ Watch the code walkthrough (MP4, 4:49)](global-mobility-estimator-walkthrough.mp4) · Loom: LINK TO FOLLOW

The tool and the code, scene by scene: the cost estimate for the test case, the immigration
tab, the rules data and the calculation engine. The voice-over is generated with Kokoro
text-to-speech, reading my script.

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

Then open http://127.0.0.1:8000/ for the tool; the API is under /api/. Click "Calculate
employer cost" to run the candidate pack's test case, which the form loads at the start.
Nothing else is needed for local use, not even Node:
there is no database to set up, and without `DJANGO_SECRET_KEY` a random key is made at
each start. For a shared server, set the variables listed in `.env.example` in the
environment (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`).

## Front end

React and TypeScript in `frontend/src`, with two tabs over one form:

| File | What it shows |
|---|---|
| `CostForm.tsx` | The inputs of spec section 4, the benefits, the method settings, and the API's message beside each wrong field |
| `Results.tsx` | Method used, the cost table with a source link on every line, other methods with line-by-line differences, the working, the check against the ESTV calculator, the duration advice, assumptions and sources |
| `Immigration.tsx` | Eligibility, requirements for the work permit, business visit, passport and employer, the timeline and the fees |

The built files in `frontend/dist` are committed and Django serves them, so running the
tool needs only Python. To change the front end you need Node 18 or later:

```bash
cd frontend
npm install
npm run build        # type-checks, then rebuilds frontend/dist
npm run dev          # live reload on http://localhost:5173, with runserver on :8000 for /api
```

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

The tests run the candidate pack's test case through the engine and the API and check the
totals, every tax band edge, the tax-on-tax loop against its closed form, the Swiss tax
against the official tables, the 24-month rules, bad input (HTTP 400 with a message, never
a crash) and that every figure links to an official https page.

## Sources and check 15

Every rule in `estimator/rules/rules_2026.json` names the official page it comes from, and
the tool shows that link beside each figure. All 54 pages were opened again on 4 November
2026; the result is in [docs/source-check.md](docs/source-check.md).

**One figure against its source.** The hypothetical Swiss income tax of the test case can be
repeated on the official [ESTV tax calculator](https://swisstaxcalculator.estv.admin.ch):

1. Choose the income and wealth tax for tax year 2026.
2. Place of residence 8001 Zürich; a single person, no children, no church affiliation.
3. Enter the taxable income: CHF 152,400 for cantonal and municipal tax, CHF 153,500 for
   federal tax: the taxable incomes under "Show working" in the tool, rounded down to CHF 100
   as the tariffs do.
4. The calculator shows federal tax CHF 7,461, cantonal tax CHF 10,820 and municipal tax
   CHF 13,553, plus the CHF 24 Personalsteuer. The tool gives CHF 7,460.55, 10,819.55 and
   13,552.91: the calculator rounds to whole francs, and the Personalsteuer is not part of
   the hypothetical tax. The tool shows this comparison in its "Check against an official
   source" box.

## AI tools used

Claude was used for finding and reading the official UK and Swiss sources, and writing the specification with the rules, decisions and expected figures.
