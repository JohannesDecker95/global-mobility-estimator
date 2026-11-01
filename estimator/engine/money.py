"""Money helpers. Every amount is a Decimal; rounding happens only where a rule says so."""
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

D = Decimal
ZERO = Decimal(0)
PENNY = Decimal("0.01")


def pence(x: Decimal) -> Decimal:
    """Round to the penny, half up: used when a line enters the cost table."""
    return x.quantize(PENNY, rounding=ROUND_HALF_UP)


def round_down(x: Decimal, step: Decimal) -> Decimal:
    """Round down to a multiple of step (CHF 100 of income, 5 Rappen of tax)."""
    return (x / step).to_integral_value(rounding=ROUND_FLOOR) * step


def positive(x: Decimal) -> Decimal:
    return x if x > 0 else ZERO
