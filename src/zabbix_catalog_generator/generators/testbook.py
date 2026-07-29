"""Build and export qualification scenarios from parsed Zabbix probes."""

from __future__ import annotations

import re
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from ..models import ProbeDefinition, TestCase, TriggerDefinition
from ..scenarios import Scenario, load_scenarios

TESTBOOK_HEADERS: dict[str, tuple[str, ...]] = {
    "policy_name": ("Nom de la politique", "Politique", "Policy name", "Policy"),
    "resource": ("Ressource", "Resource"),
    "trigger_name": (
        "Nom du déclencheur",
        "Déclencheur",
        "Détection",
        "Trigger name",
        "Trigger",
        "Detection",
    ),
    "severity": ("Sévérité", "Severite", "Severity"),
    "expression": ("Expression", "Expression du déclencheur", "Trigger expression"),
    "recovery_expression": (
        "Expression de rétablissement",
        "Expression de retablissement",
        "Recovery expression",
    ),
    "macros": ("Macros", "Macro", "Macros du déclencheur", "Trigger macros"),
    "tags": ("Tags", "Tags du déclencheur", "Trigger tags"),
    "test_code": ("Code test", "Code du test", "Test code"),
    "scenario": ("Scénario", "Scenario"),
    "objective": ("Objectif", "Objective"),
    "prerequisites": ("Prérequis", "Prerequis", "Prerequisites"),
    "procedure": ("Procédure", "Procedure", "Action", "Actions"),
    "expected_result": ("Résultat attendu", "Resultat attendu", "Expected result"),
    "tester": ("Testeur", "Tester"),
    "date": ("Date", "Date d'exécution", "Execution date"),
    "status": ("Statut", "Status"),
    "evidence": ("Preuve", "Evidence"),
    "comments": ("Commentaires", "Commentaire", "Comments", "Comment"),
    "generation": ("Génération", "Generation", "Mode de génération"),
}

_REQUIRED_HEADERS = {
    "policy_name",
    "resource",
    "trigger_name",
    "test_code",
    "scenario",
    "expected_result",
}

_USER_MACRO_PATTERN = re.compile(r"\{\$[^{}]+\}")
_PLACEHOLDER_PATTERN = re.compile(r"\$\{([a-zA-Z0-9_.]+)\}")
_TIME_FUNCTION_PATTERN = re.compile(r"\b(?:avg|min|max|sum|count|trendavg|trendmin|trendmax)\s*\(", re.I)


def _normalise(value: object) -> str:
    """Normalise an Excel header for resilient matching."""

    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _find_header_row(sheet: Worksheet) -> tuple[int, dict[str, int]]:
    expected = {
        _normalise(label): field
        for field, labels in TESTBOOK_HEADERS.items()
        for label in labels
    }

    for row in range(1, min(sheet.max_row, 50) + 1):
        columns: dict[str, int] = {}
        for column in range(1, sheet.max_column + 1):
            field = expected.get(_normalise(sheet.cell(row, column).value))
            if field:
                columns[field] = column

        if _REQUIRED_HEADERS.issubset(columns):
            return row, columns

    missing = ", ".join(sorted(_REQUIRED_HEADERS))
    raise ValueError(
        "The testbook model does not contain the expected header row "
        f"(required fields: {missing})"
    )


def _capture_row_style(
    sheet: Worksheet,
    source_row: int,
) -> tuple[float | None, list[dict[str, object]]]:
    styles: list[dict[str, object]] = []
    for column in range(1, sheet.max_column + 1):
        source = sheet.cell(source_row, column)
        styles.append(
            {
                "style": copy(source._style),
                "number_format": source.number_format,
                "alignment": copy(source.alignment),
                "protection": copy(source.protection),
            }
        )
    return sheet.row_dimensions[source_row].height, styles


def _apply_row_style(
    sheet: Worksheet,
    target_row: int,
    row_style: tuple[float | None, list[dict[str, object]]],
) -> None:
    height, styles = row_style
    sheet.row_dimensions[target_row].height = height
    for column, style in enumerate(styles, start=1):
        target = sheet.cell(target_row, column)
        target._style = copy(style["style"])
        target.number_format = str(style["number_format"])
        target.alignment = copy(style["alignment"])
        target.protection = copy(style["protection"])


def _first_data_row(sheet: Worksheet, header_row: int) -> int:
    """Return the first styled data row, allowing one spacer row below headers."""

    next_row = header_row + 1
    if next_row <= sheet.max_row and all(
        sheet.cell(next_row, column).value is None
        for column in range(1, sheet.max_column + 1)
    ):
        return next_row + 1
    return next_row


def _write_test_case(
    sheet: Worksheet,
    row: int,
    columns: dict[str, int],
    test_case: TestCase,
) -> None:
    for field, column in columns.items():
        sheet.cell(row, column).value = getattr(test_case, field)


def _trigger_macros(probe: ProbeDefinition, trigger: TriggerDefinition) -> str:
    """Return only user macros referenced by a trigger, preserving expression order."""

    values = dict(probe.template_macros)
    seen: set[str] = set()
    lines: list[str] = []
    expressions = f"{trigger.expression}\n{trigger.recovery_expression}"
    for macro in _USER_MACRO_PATTERN.findall(expressions):
        if macro in seen:
            continue
        seen.add(macro)
        value = values.get(macro)
        lines.append(f"{macro}={value}" if value is not None else f"{macro}=<non définie>")
    return "\n".join(lines)


def _trigger_tags(trigger: TriggerDefinition) -> str:
    return "\n".join(
        f"{name}={value}" if value else name
        for name, value in trigger.tags
    )


def _is_applicable(scenario: Scenario, trigger: TriggerDefinition, macros: str) -> bool:
    rule = scenario.applies.casefold()
    if rule == "always":
        return True
    if rule == "uses_macros":
        return bool(macros)
    if rule == "recovery_expression":
        return bool(trigger.recovery_expression.strip())
    if rule == "nodata":
        return "nodata(" in trigger.expression.casefold()
    if rule == "time_window":
        return bool(_TIME_FUNCTION_PATTERN.search(trigger.expression))
    if rule == "dependencies":
        return bool(getattr(trigger, "dependencies", ()))
    raise ValueError(f"Unknown scenario applicability rule: {scenario.applies}")


def _render(text: str, context: dict[str, str]) -> str:
    """Replace documented ${namespace.field} variables and keep unknown ones visible."""

    return _PLACEHOLDER_PATTERN.sub(
        lambda match: context.get(match.group(1), match.group(0)),
        text,
    )


def _render_context(
    probe: ProbeDefinition,
    trigger: TriggerDefinition,
    macros: str,
    tags: str,
) -> dict[str, str]:
    return {
        "policy.name": probe.template_name,
        "resource.name": probe.name,
        "resource.key": probe.key,
        "resource.delay": probe.delay or "non défini",
        "trigger.name": trigger.name,
        "trigger.expression": trigger.expression or "non définie",
        "trigger.recovery_expression": trigger.recovery_expression or "non définie",
        "trigger.severity": trigger.severity,
        "trigger.description": trigger.description,
        "trigger.macros": macros or "Aucune macro utilisée.",
        "trigger.tags": tags or "Aucun tag configuré.",
    }


def build_test_cases(
    probes: list[ProbeDefinition],
    *,
    scenarios_path: str | Path | None = None,
) -> list[TestCase]:
    """Create applicable qualification scenarios for enabled trigger definitions."""

    scenarios = load_scenarios(scenarios_path)
    test_cases: list[TestCase] = []
    for probe in probes:
        for trigger in probe.triggers:
            macros = _trigger_macros(probe, trigger)
            tags = _trigger_tags(trigger)
            context = _render_context(probe, trigger, macros, tags)
            for scenario in scenarios:
                if not _is_applicable(scenario, trigger, macros):
                    continue
                test_cases.append(
                    TestCase(
                        policy_name=probe.template_name,
                        resource=probe.name,
                        trigger_name=trigger.name,
                        severity=trigger.severity,
                        expression=trigger.expression,
                        recovery_expression=trigger.recovery_expression,
                        macros=macros,
                        tags=tags,
                        test_code=scenario.code,
                        scenario=scenario.title,
                        objective=_render(scenario.objective, context),
                        prerequisites=_render(scenario.prerequisites, context),
                        procedure=_render(scenario.procedure, context),
                        expected_result=_render(scenario.expected_result, context),
                    )
                )
    return test_cases


def generate_testbook(
    model_path: str | Path,
    output_path: str | Path,
    test_cases: list[TestCase],
    *,
    sheet_name: str | None = None,
) -> Path:
    """Populate a copy of the Excel testbook model with generated test cases."""

    output = Path(output_path)
    workbook = load_workbook(Path(model_path))
    sheet = workbook[sheet_name] if sheet_name else workbook.active
    header_row, columns = _find_header_row(sheet)
    first_data_row = _first_data_row(sheet, header_row)
    row_style = _capture_row_style(sheet, first_data_row)

    if sheet.max_row >= first_data_row:
        sheet.delete_rows(first_data_row, sheet.max_row - first_data_row + 1)

    for offset, test_case in enumerate(test_cases):
        row = first_data_row + offset
        _apply_row_style(sheet, row, row_style)
        _write_test_case(sheet, row, columns, test_case)

    sheet.auto_filter.ref = f"A{header_row}:{sheet.cell(header_row, sheet.max_column).coordinate}"
    sheet.freeze_panes = f"A{first_data_row}"
    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    return output
