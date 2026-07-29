"""Load qualification scenarios from a YAML configuration file."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True, frozen=True)
class Scenario:
    """A configurable qualification scenario."""

    code: str
    title: str
    applies: str
    objective: str
    prerequisites: str
    procedure: str
    expected_result: str


def _scenario_from_mapping(raw: dict[str, Any], index: int) -> Scenario:
    required = ("code", "title", "objective", "procedure", "expected_result")
    missing = [field for field in required if not str(raw.get(field, "")).strip()]
    if missing:
        raise ValueError(
            f"Invalid scenario at index {index}: missing required fields {', '.join(missing)}"
        )

    applies = raw.get("applies", "always")
    if isinstance(applies, dict):
        applies = applies.get("type", "always")

    return Scenario(
        code=str(raw["code"]).strip(),
        title=str(raw["title"]).strip(),
        applies=str(applies or "always").strip(),
        objective=str(raw["objective"]).strip(),
        prerequisites=str(raw.get("prerequisites", "")).strip(),
        procedure=str(raw["procedure"]).strip(),
        expected_result=str(raw["expected_result"]).strip(),
    )


def load_scenarios(path: str | Path | None = None) -> list[Scenario]:
    """Load and validate scenarios from YAML.

    When ``path`` is omitted, the scenario repository shipped with the package is used.
    """

    source = Path(path) if path is not None else files(__package__).joinpath("scenarios.yaml")
    with source.open("r", encoding="utf-8") as stream:
        document = yaml.safe_load(stream) or []

    if not isinstance(document, list):
        raise ValueError("The scenario configuration must contain a YAML list")

    scenarios = [_scenario_from_mapping(raw, index) for index, raw in enumerate(document, 1)]
    codes = [scenario.code for scenario in scenarios]
    duplicates = sorted({code for code in codes if codes.count(code) > 1})
    if duplicates:
        raise ValueError(f"Duplicate scenario codes: {', '.join(duplicates)}")
    return scenarios
