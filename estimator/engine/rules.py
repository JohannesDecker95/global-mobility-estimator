"""Rules data: every rate, threshold and fee with the official page it comes from.

The values live in ``estimator/rules/rules_<year>.json``, not in the code. The engine
reads them through a ``RuleSet`` and records the rule IDs each figure used, so the API
can send the source links along with the numbers (gate check 3).

All numbers are read as Decimal. Pure Python on purpose: no Django import, so the engine and its tests run on their own.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
DEFAULT_RULES_FILE = RULES_DIR / "rules_2026.json"

RULE_ID_PATTERN = re.compile(r"^[A-Z]{2,4}(-[A-Z0-9]{1,5})?-\d{2}$")

# Hosts accepted as official (check 9): governments, tax authorities and regulators.
OFFICIAL_HOST_SUFFIXES = (
    "gov.uk",  # GOV.UK, HMRC, Home Office, assets.publishing.service.gov.uk
    "admin.ch",  # Swiss federal offices: ESTV, BSV, fedpol
    "ahv-iv.ch",  # Informationsstelle AHV/IV, the compensation offices' official leaflets
    "zh.ch",  # Canton of Zurich
    "stadt-zuerich.ch",  # City of Zurich
    "ne.ch",  # Canton of Neuchatel (copy of the federal tariff)
)


class RulesError(ValueError):
    """The rules file is broken or a rule is missing."""


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    publisher: str
    url: str


@dataclass(frozen=True)
class Rule:
    rule_id: str
    jurisdiction: str
    topic: str
    description: str
    unit: str | None
    valid_from: str | None
    valid_to: str | None
    value: Any
    sources: tuple[Source, ...]

    @property
    def urls(self) -> list[str]:
        return [s.url for s in self.sources]

    def __getitem__(self, key: str) -> Any:
        """Shortcut for a field of the value: rules["UK-IT-01"]["personal_allowance"]."""
        if not isinstance(self.value, dict) or key not in self.value:
            raise RulesError(f"{self.rule_id} has no value '{key}'")
        return self.value[key]

    def citation(self) -> dict:
        """What the API sends next to a figure that used this rule."""
        return {
            "rule_id": self.rule_id,
            "description": self.description,
            "sources": [
                {"title": s.title, "publisher": s.publisher, "url": s.url}
                for s in self.sources
            ],
        }


class RuleSet:
    """All rules of one rules file, looked up by rule ID."""

    def __init__(self, data: dict, origin: str = "<data>"):
        self.origin = origin
        self.tax_year = data.get("tax_year")
        self.schema_version = data.get("schema_version")
        errors = validate(data)
        if errors:
            raise RulesError(f"{origin}: " + "; ".join(errors))
        sources = {
            sid: Source(sid, s["title"], s["publisher"], s["url"])
            for sid, s in data["sources"].items()
        }
        self._rules = {
            r["rule_id"]: Rule(
                rule_id=r["rule_id"],
                jurisdiction=r["jurisdiction"],
                topic=r["topic"],
                description=r["description"],
                unit=r.get("unit"),
                valid_from=r.get("valid_from"),
                valid_to=r.get("valid_to"),
                value=r.get("value"),
                sources=tuple(sources[sid] for sid in r["sources"]),
            )
            for r in data["rules"]
        }
        self.sources = sources

    def __getitem__(self, rule_id: str) -> Rule:
        try:
            return self._rules[rule_id]
        except KeyError:
            raise RulesError(f"Unknown rule ID '{rule_id}' in {self.origin}") from None

    def __contains__(self, rule_id: str) -> bool:
        return rule_id in self._rules

    def __iter__(self):
        return iter(self._rules.values())

    def __len__(self) -> int:
        return len(self._rules)

    def citations(self, rule_ids: Iterable[str]) -> list[dict]:
        """Citations for several rules, in order, without duplicates."""
        seen, out = set(), []
        for rid in rule_ids:
            if rid not in seen:
                seen.add(rid)
                out.append(self[rid].citation())
        return out

    def by_topic(self, topic: str) -> list[Rule]:
        return [r for r in self if r.topic == topic]


def _read(path: Path) -> dict:
    # Every number becomes Decimal, whole numbers too, so money maths never mixes in floats
    # (an int divided by 100 would otherwise turn into a float).
    with open(path, encoding="utf-8") as fh:
        return json.load(fh, parse_float=Decimal, parse_int=Decimal)


def load_rules(path: str | Path | None = None) -> RuleSet:
    """Load and validate a rules file. The default file is cached."""
    if path is None:
        return _default_rules()
    path = Path(path)
    return RuleSet(_read(path), origin=path.name)


@lru_cache(maxsize=1)
def _default_rules() -> RuleSet:
    return RuleSet(_read(DEFAULT_RULES_FILE), origin=DEFAULT_RULES_FILE.name)


def is_official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(
        host == suffix or host.endswith("." + suffix)
        for suffix in OFFICIAL_HOST_SUFFIXES
    )


def validate(data: dict) -> list[str]:
    """Return every problem found in a rules file; an empty list means it is valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["the file must contain a JSON object"]
    sources = data.get("sources")
    rules = data.get("rules")
    if not isinstance(sources, dict) or not sources:
        errors.append("'sources' must be a non-empty object")
        sources = {}
    if not isinstance(rules, list) or not rules:
        errors.append("'rules' must be a non-empty list")
        rules = []

    for sid, s in sources.items():
        for field in ("title", "publisher", "url"):
            if not isinstance(s, dict) or not s.get(field):
                errors.append(f"source '{sid}' has no {field}")
        if isinstance(s, dict) and s.get("url") and not is_official_url(s["url"]):
            errors.append(f"source '{sid}' is not an official https page: {s['url']}")

    seen, used = set(), set()
    for i, r in enumerate(rules):
        rid = r.get("rule_id") if isinstance(r, dict) else None
        label = rid or f"rules[{i}]"
        if not rid:
            errors.append(f"{label} has no rule_id")
            continue
        if not RULE_ID_PATTERN.match(rid):
            errors.append(f"{label}: rule_id does not look like 'UK-IT-01'")
        if rid in seen:
            errors.append(f"{label} appears twice")
        seen.add(rid)
        for field in ("jurisdiction", "topic", "description"):
            if not r.get(field):
                errors.append(f"{label} has no {field}")
        if "value" not in r:
            errors.append(f"{label} has no value (use null for a rule without numbers)")
        refs = r.get("sources")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{label} cites no source")
            continue
        for sid in refs:
            if sid not in sources:
                errors.append(f"{label} cites unknown source '{sid}'")
            used.add(sid)
    for sid in sources:
        if sid not in used:
            errors.append(f"source '{sid}' is not cited by any rule")
    return errors
