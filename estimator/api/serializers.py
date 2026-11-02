"""Input validation for the API (subtasks 14 and 15).

Each field gives a plain message when the input is missing or wrong (check 12), and the
validated data becomes an engine Case. The inputs follow spec section 4.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from rest_framework import serializers

from ..engine.inputs import (CATEGORIES, CURRENCIES, HOUSING, MAX_MONTHS, MIN_MONTHS, MONTHLY, MOVING_COSTS,
                             ONE_OFF, OTHER_CASH, OTHER_IN_KIND, RELOCATION_ALLOWANCE, TEMPORARY_HOUSING, Benefit,
                             Case)

# Stays start on the 6th of a month inside UK tax year 2026/27, the year the rules cover
# (decision of 2 November 2026); see check_dates.
FIRST_START = date(2026, 4, 6)
LAST_START = date(2027, 3, 6)

CATEGORY_LABELS = {
    HOUSING: "Housing",
    TEMPORARY_HOUSING: "Temporary housing",
    MOVING_COSTS: "Moving costs",
    RELOCATION_ALLOWANCE: "Relocation cash allowance",
    OTHER_CASH: "Other cash allowance",
    OTHER_IN_KIND: "Other benefit in kind",
}
TIMING_LABELS = {MONTHLY: "Monthly for the whole stay", ONE_OFF: "One-off at the start"}
SPONSOR_SIZES = {"medium_or_large": "Medium or large", "small": "Small"}


def money(label: str, example: str, required: bool = True, default=None) -> serializers.DecimalField:
    """A non-negative amount with at most 2 decimals and readable messages."""
    must = f"{label} must be a number of 0 or more, for example {example}."
    kwargs = {"required": required}
    if not required:
        kwargs["default"] = default
    return serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal(0), coerce_to_string=True,
        error_messages={
            "required": f"{label} is required.",
            "null": f"{label} is required.",
            "invalid": must,
            "min_value": must,
            "max_digits": f"{label} is too large.",
            "max_whole_digits": f"{label} is too large.",
            "max_decimal_places": f"{label} can have at most 2 decimals.",
        }, **kwargs)


def choice(label: str, choices: dict, unsupported: str, default=None) -> serializers.ChoiceField:
    kwargs = {"required": default is None}
    if default is not None:
        kwargs["default"] = default
    return serializers.ChoiceField(
        choices=list(choices.items()),
        error_messages={
            "required": f"{label} is required.",
            "null": f"{label} is required.",
            "invalid_choice": f'"{{input}}" is not supported yet. {unsupported}',
        }, **kwargs)


def flag(label: str, default: bool) -> serializers.BooleanField:
    return serializers.BooleanField(
        default=default,
        error_messages={"invalid": f"{label} must be true or false.", "null": f"{label} must be true or false."})


def whole(label: str, lo: int, hi: int, required: bool = True, default=None) -> serializers.IntegerField:
    must = f"{label} must be a whole number from {lo} to {hi}."
    kwargs = {"required": required}
    if not required:
        kwargs["default"] = default
    return serializers.IntegerField(
        min_value=lo, max_value=hi,
        error_messages={"required": f"{label} is required.", "null": f"{label} is required.",
                        "invalid": must, "min_value": must, "max_value": must, "max_string_length": must},
        **kwargs)


def check_dates(start: date, end: date) -> tuple[int, int]:
    """Return (months, start offset from 6 April 2026), or raise a readable error.

    The stay starts on the 6th of a month from 6 April 2026 to 6 March 2027, so it starts
    inside the tax year the rules cover, and ends on the 5th of a month 12 to 60 months
    later, so it is whole months. Later tax years use the 2026/27 rates, which the response
    marks for each year.
    """
    errors = {}
    if start.day != 6 or not FIRST_START <= start <= LAST_START:
        errors["start_date"] = [
            "Start date must be the 6th of a month from 6 April 2026 to 6 March 2027, so the stay "
            "starts in UK tax year 2026/27, the year the rules cover."]
    if end <= start:
        errors["end_date"] = ["End date must be after the start date."]
    elif end.day != 5:
        errors["end_date"] = ["End date must be the 5th of a month, so the stay is whole months "
                              "(for example 5 April 2028)."]
    if errors:
        raise serializers.ValidationError(errors)
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if not MIN_MONTHS <= months <= MAX_MONTHS:
        raise serializers.ValidationError({"end_date": [
            f"The assignment must last {MIN_MONTHS} to {MAX_MONTHS} months; these dates give {months}."]})
    offset = (start.year - FIRST_START.year) * 12 + (start.month - FIRST_START.month)
    return months, offset


class BenefitSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=80, error_messages={
        "required": "Each benefit needs a name.", "blank": "Each benefit needs a name.",
        "max_length": "A benefit name can have at most 80 characters."})
    category = choice("Category", CATEGORY_LABELS,
                      "Choose housing, temporary_housing, moving_costs, relocation_allowance, "
                      "other_cash_allowance or other_benefit_in_kind.")
    amount = money("Amount", "3000")
    currency = choice("Currency", {c: c for c in CURRENCIES}, "Use GBP or CHF.", default="GBP")
    timing = choice("Timing", TIMING_LABELS, "Use monthly or one_off.")

    def to_benefit(self, data: dict) -> Benefit:
        return Benefit(data["label"], data["category"], data["amount"], data["currency"], data["timing"])


class OptionsSerializer(serializers.Serializer):
    """Method switches (spec sections 16 and 17). The defaults are the tool's method."""
    twr_rule = flag("Temporary-workplace relief", True)
    ahv_full_base = flag("Swiss AHV on the full assignment pay", True)
    pillar2 = flag("Pillar 2", True)


class EstimateSerializer(serializers.Serializer):
    home_country = choice("Home country", {"CH": "Switzerland"}, "This version supports Switzerland (CH).",
                          default="CH")
    home_city = choice("Home city", {"zurich": "Zurich (city)"}, "This version supports the city of Zurich.",
                       default="zurich")
    host_country = choice("Host country", {"GB": "United Kingdom"}, "This version supports the United Kingdom (GB).",
                          default="GB")
    host_city = choice("Host city", {"london": "London"},
                       "This version uses England and Northern Ireland rates for London; Scotland is not supported.",
                       default="london")
    start_date = serializers.DateField(error_messages={
        "required": "Start date is required.", "null": "Start date is required.",
        "invalid": "Start date must be a date like 2026-04-06."})
    end_date = serializers.DateField(error_messages={
        "required": "End date is required.", "null": "End date is required.",
        "invalid": "End date must be a date like 2028-04-05."})
    nationality = choice("Nationality", {"CH": "Swiss"}, "This version supports Swiss nationals (CH).", default="CH")
    marital_status = choice("Marital status", {"single": "Single", "married": "Married"},
                            "This version supports single.", default="single")
    children = whole("Children", 0, 20, required=False, default=0)
    months_with_employer = whole("Months worked for the employer before the move", 0, 600)
    salary_chf = money("Base salary", "150000")
    bonus_chf = money("Bonus", "20000", required=False, default=Decimal(0))
    fx_chf_per_gbp = serializers.DecimalField(
        max_digits=8, decimal_places=4, min_value=Decimal("0.0001"),
        error_messages={
            "required": "Exchange rate is required.", "null": "Exchange rate is required.",
            "invalid": "Exchange rate must be a number greater than 0, in CHF per £1, for example 1.10.",
            "min_value": "Exchange rate must be a number greater than 0, in CHF per £1, for example 1.10.",
            "max_digits": "Exchange rate is too large.", "max_whole_digits": "Exchange rate is too large.",
            "max_decimal_places": "Exchange rate can have at most 4 decimals."})
    sponsor_size = choice("UK sponsor size", SPONSOR_SIZES, "Use medium_or_large or small.",
                          default="medium_or_large")
    sponsor_licence_held = flag("Sponsor licence already held", False)
    continuing_employment = flag("Swiss employment contract continues", True)
    housing_reasonable = flag("Housing reasonable for one person", True)
    swiss_home_kept = flag("Employee keeps a home in Switzerland", False)
    art17_exception = flag("Article 17 exception agreed", False)
    advice_from = whole("Duration advice from", MIN_MONTHS, MAX_MONTHS, required=False, default=MIN_MONTHS)
    advice_to = whole("Duration advice to", MIN_MONTHS, MAX_MONTHS, required=False, default=MAX_MONTHS)
    benefits = serializers.ListField(
        child=BenefitSerializer(), required=False, default=list, max_length=20,
        error_messages={"not_a_list": "Benefits must be a list.", "max_length": "At most 20 benefits."})
    options = OptionsSerializer(required=False)

    def validate_marital_status(self, value):
        if value != "single":
            raise serializers.ValidationError("Married is not supported yet. This version supports single.")
        return value

    def validate_children(self, value):
        if value:
            raise serializers.ValidationError("Children are not supported yet. This version supports none.")
        return value

    def validate(self, data):
        data["months"], data["start_offset"] = check_dates(data["start_date"], data["end_date"])
        if data["advice_from"] > data["advice_to"]:
            raise serializers.ValidationError({"advice_to": ["Duration advice to must not be before from."]})
        return data

    def to_case(self) -> Case:
        d = self.validated_data
        options = {**OptionsSerializer().to_internal_value({}), **(d.get("options") or {})}
        return Case(
            months=d["months"], start_offset=d["start_offset"],
            salary_chf=d["salary_chf"], bonus_chf=d["bonus_chf"],
            fx_chf_per_gbp=d["fx_chf_per_gbp"],
            benefits=tuple(BenefitSerializer().to_benefit(b) for b in d["benefits"]),
            months_with_employer=d["months_with_employer"],
            continuing_employment=d["continuing_employment"], housing_reasonable=d["housing_reasonable"],
            swiss_home_kept=d["swiss_home_kept"], art17_exception=d["art17_exception"],
            sponsor_large=d["sponsor_size"] == "medium_or_large", sponsor_licence_held=d["sponsor_licence_held"],
            pillar2=options["pillar2"], ahv_full_base=options["ahv_full_base"], twr_rule=options["twr_rule"],
        )


class ImmigrationQuerySerializer(serializers.Serializer):
    """Query parameters of GET /api/immigration/."""
    nationality = choice("Nationality", {"CH": "Swiss"}, "This version supports Swiss nationals (CH).")
    host = choice("Host country", {"GB": "United Kingdom"}, "This version supports the United Kingdom (GB).")
    sponsor_size = choice("UK sponsor size", SPONSOR_SIZES, "Use medium_or_large or small.",
                          default="medium_or_large")
    months = whole("Months", MIN_MONTHS, MAX_MONTHS, required=False, default=24)
    sponsor_licence_held = flag("Sponsor licence already held", False)
    salary_gbp = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal(0), required=False, default=None, allow_null=True,
        error_messages={"invalid": "Salary must be a number of 0 or more in £ a year, for example 136363.64.",
                        "min_value": "Salary must be a number of 0 or more in £ a year, for example 136363.64.",
                        "max_digits": "Salary is too large.", "max_whole_digits": "Salary is too large.",
                        "max_decimal_places": "Salary can have at most 2 decimals."})
    months_with_employer = whole("Months worked for the employer before the move", 0, 600,
                                 required=False, default=None)
