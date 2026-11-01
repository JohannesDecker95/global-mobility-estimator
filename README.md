# Global Mobility Estimator

## Rules data

Every rate, threshold and fee the estimator uses lives in one file,
`estimator/rules/rules_2026.json`, never in the code. Each rule has an ID (for example
`UK-IT-01`), its value and the official page it comes from. The engine reads the rules
through `estimator/engine/rules.py` and can return the source links with every figure.

When rates change, edit or add a rules file; the loader refuses a file with a missing
field, an unknown source or a link that is not an official https page.

Run the rules tests:

```bash
python manage.py test estimator
```
