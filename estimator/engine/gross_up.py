"""Tax on tax: the gross-up loops (subtask 11).

Rule IDs: UK-TE-01, UK-TE-02 (T = UKTax(I + T)), UK-BEN-07 (contributions the employer
bears are UK earnings), CH-AHV-01, CH-AHV-02 (net-to-gross for AHV), UK-NI-01.

Three loops, all fixed-point iterations started at zero. Each round moves the result
by the marginal rate (at most 60% for tax, a little more with contributions), so they
converge; the round limit only guards against bad code.

- gross_up:        T = UKTax(I + T)                        the brief's formula
- solve_swiss:     T and E together while Swiss social security applies and the
                   employer also bears the extra AHV on the assignment pay (section 16)
- solve_uk:        G = UKTax(I + G) + NICee(C + G)          under UK National Insurance
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from .money import ZERO
from .rules import RuleSet, load_rules
from .swiss_social import employee_contributions
from .uk_tax import income_tax, nic_employee


class GrossUpError(RuntimeError):
    """The loop did not settle within the round limit."""


@dataclass
class Trace:
    rounds: list[tuple[int, Decimal]] = field(default_factory=list)   # (round, T after it)

    @property
    def count(self) -> int:
        return len(self.rounds)


def _limits(rules: RuleSet) -> tuple[Decimal, int]:
    r = rules["UK-TE-02"]
    return r["tolerance"], int(r["max_rounds"])


def gross_up(i: Decimal, rules: RuleSet | None = None) -> tuple[Decimal, Trace]:
    """Solve T = UKTax(I + T) by iteration."""
    r = rules or load_rules()
    tol, max_rounds = _limits(r)
    t, trace = ZERO, Trace()
    for n in range(1, max_rounds + 1):
        new = income_tax(i + t, r)
        trace.rounds.append((n, new))
        if abs(new - t) < tol:
            return new, trace
        t = new
    raise GrossUpError(f"No convergence after {max_rounds} rounds")


@dataclass(frozen=True)
class SwissBranch:
    tax: Decimal               # T, UK income tax the employer pays
    taxable_pay: Decimal       # I, UK taxable pay before tax
    extra_employee_ss: Decimal # Swiss employee contributions on the assignment extras, borne by the employer
    extra_employer_ss: Decimal # employer contributions on the same extras
    grossed_up_ss: Decimal     # E, the part of the employee contributions added to the AHV base
    ahv_extra_base: Decimal    # what the assignment adds to the AHV base, GBP
    trace: Trace


def solve_swiss(*, home_pay: Decimal, hypo_tax: Decimal, uk_base: Decimal,
                ahv_cash: Decimal, ahv_in_kind: Decimal, months: int, fx: Decimal,
                full_base: bool, rules: RuleSet | None = None) -> SwissBranch:
    """Solve T and E together.

    uk_base     I as the brief defines it: net home pay plus taxable benefits
    ahv_cash    cash assignment pay that is AHV wage (relocation and other cash allowances)
    ahv_in_kind benefits in kind that are AHV wage (housing)
    AHV cash base = home pay + (T - hypothetical tax) + cash pay + E      (grossed up, CH-AHV-01/02)
    AHV base      = AHV cash base + in-kind pay                         (not grossed up)
    """
    r = rules or load_rules()
    tol, max_rounds = _limits(r)

    def ee(base):
        return employee_contributions(base, r, months, chf_per_unit=fx)

    t, e, trace = ZERO, ZERO, Trace()
    for n in range(1, max_rounds + 1):
        if full_base:
            cash_extra = t - hypo_tax + ahv_cash
            e_new = ee(home_pay + cash_extra + e) - ee(home_pay)
            extra_ee = ee(home_pay + cash_extra + e + ahv_in_kind) - ee(home_pay)
        else:
            cash_extra = e_new = extra_ee = ZERO
        i = uk_base + extra_ee                                     # UK-BEN-07
        t_new = income_tax(i + t, r)
        trace.rounds.append((n, t_new))
        if abs(t_new - t) < tol and abs(e_new - e) < tol:
            t, e = t_new, e_new
            return SwissBranch(t, i, extra_ee, extra_ee, e,
                               (cash_extra + e + ahv_in_kind) if full_base else ZERO, trace)
        t, e = t_new, e_new
    raise GrossUpError(f"No convergence after {max_rounds} rounds")


@dataclass(frozen=True)
class UKBranch:
    tax: Decimal
    employee_ni: Decimal
    taxable_pay: Decimal
    trace: Trace


def solve_uk(*, cash: Decimal, in_kind: Decimal, months: int,
             rules: RuleSet | None = None) -> UKBranch:
    """Solve G = UKTax(I + G) + NICee(C + G): tax and employee NI the employer pays."""
    r = rules or load_rules()
    tol, max_rounds = _limits(r)
    i = cash + in_kind
    g, trace = ZERO, Trace()
    for n in range(1, max_rounds + 1):
        new = income_tax(i + g, r) + nic_employee(cash + g, months, r)
        trace.rounds.append((n, new))
        if abs(new - g) < tol:
            g = new
            return UKBranch(income_tax(i + g, r), nic_employee(cash + g, months, r), i, trace)
        g = new
    raise GrossUpError(f"No convergence after {max_rounds} rounds")
