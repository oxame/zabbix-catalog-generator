from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from zabbix_catalog_generator.generators import (
    build_test_cases,
    generate_catalogue,
    generate_testbook,
)
from zabbix_catalog_generator.models import ProbeDefinition, TestCase, TriggerDefinition


def _probe(*triggers: TriggerDefinition) -> ProbeDefinition:
    return ProbeDefinition(
        template_name="Linux by Zabbix agent",
        template_description="",
        name="CPU utilization",
        key="system.cpu.util",
        description="",
        delay="1m",
        item_type="ZABBIX_PASSIVE",
        value_type="FLOAT",
        units="%",
        history="7d",
        trends="365d",
        template_macros=(
            ("{$CPU.MAX}", "90"),
            ("{$CPU.RECOVERY}", "80"),
            ("{$UNUSED}", "123"),
        ),
        triggers=triggers,
    )


def _create_model(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tests"
    sheet.append(
        [
            "Nom de la politique",
            "Ressource",
            "Nom du déclencheur",
            "Sévérité",
            "Type de test",
            "Macros",
            "Prérequis",
            "Action",
            "Résultat attendu",
            "Commentaires",
        ]
    )
    sheet.append([None] * 10)
    sheet.append([None] * 10)
    for cell in sheet[3]:
        cell.fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
        cell.font = Font(name="Arial", bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.row_dimensions[3].height = 42
    workbook.save(path)


def test_test_case_defaults_are_empty() -> None:
    test_case = TestCase(
        policy_name="Template",
        resource="Resource",
        trigger_name="Trigger",
        severity="HIGH",
        test_type="PROBLEM",
    )

    assert test_case.macros == ""
    assert test_case.prerequisites == ""
    assert test_case.action == ""
    assert test_case.expected_result == ""
    assert test_case.comments == ""


def test_build_test_cases_creates_problem_and_recovery_scenarios() -> None:
    trigger = TriggerDefinition(
        name="CPU usage is high",
        severity="HIGH",
        expression="last(/template/system.cpu.util)>{$CPU.MAX}",
        recovery_expression="last(/template/system.cpu.util)<{$CPU.RECOVERY}",
    )

    test_cases = build_test_cases([_probe(trigger)])

    assert [test_case.test_type for test_case in test_cases] == ["PROBLEM", "RECOVERY"]
    assert all(test_case.policy_name == "Linux by Zabbix agent" for test_case in test_cases)
    assert all(test_case.resource == "CPU utilization" for test_case in test_cases)
    assert all(test_case.trigger_name == "CPU usage is high" for test_case in test_cases)
    assert all(test_case.severity == "HIGH" for test_case in test_cases)
    assert all(
        test_case.macros == "{$CPU.MAX}=90\n{$CPU.RECOVERY}=80"
        for test_case in test_cases
    )


def test_build_test_cases_only_exports_macros_used_by_trigger() -> None:
    trigger = TriggerDefinition(
        name="CPU usage is high",
        expression=(
            "avg(/template/system.cpu.util,5m)>{$CPU.MAX} "
            "and last(/template/system.cpu.util)>{$CPU.MAX}"
        ),
    )

    test_cases = build_test_cases([_probe(trigger)])

    assert test_cases[0].macros == "{$CPU.MAX}=90"
    assert "{$UNUSED}" not in test_cases[0].macros


def test_build_test_cases_marks_undefined_trigger_macro() -> None:
    trigger = TriggerDefinition(
        name="CPU usage is high",
        expression="last(/template/system.cpu.util)>{$CPU.UNKNOWN}",
    )

    test_cases = build_test_cases([_probe(trigger)])

    assert test_cases[0].macros == "{$CPU.UNKNOWN}=<non définie>"


def test_build_test_cases_skips_recovery_without_expression() -> None:
    trigger = TriggerDefinition(name="CPU usage is high", severity="WARNING")

    test_cases = build_test_cases([_probe(trigger)])

    assert len(test_cases) == 1
    assert test_cases[0].test_type == "PROBLEM"


def test_generators_package_keeps_catalogue_api() -> None:
    assert callable(generate_catalogue)


def test_generate_testbook_populates_model_and_preserves_style(tmp_path: Path) -> None:
    model = tmp_path / "model.xlsx"
    output = tmp_path / "output.xlsx"
    _create_model(model)
    test_cases = [
        TestCase(
            policy_name="Linux by Zabbix agent",
            resource="CPU utilization",
            trigger_name="CPU usage is high",
            severity="HIGH",
            test_type="PROBLEM",
            macros="{$CPU.MAX}=90",
            prerequisites="Agent actif",
            action="Générer une charge CPU",
            expected_result="Le déclencheur passe en état PROBLEM.",
            comments="Test automatique",
        ),
        TestCase(
            policy_name="Linux by Zabbix agent",
            resource="CPU utilization",
            trigger_name="CPU usage is high",
            severity="HIGH",
            test_type="RECOVERY",
            macros="{$CPU.MAX}=90\n{$CPU.RECOVERY}=80",
            expected_result="Le déclencheur revient à l'état OK.",
        ),
    ]

    result = generate_testbook(model, output, test_cases)

    assert result == output
    workbook = load_workbook(output)
    sheet = workbook["Tests"]
    assert sheet.cell(3, 1).value == "Linux by Zabbix agent"
    assert sheet.cell(3, 5).value == "PROBLEM"
    assert sheet.cell(3, 6).value == "{$CPU.MAX}=90"
    assert sheet.cell(3, 9).value == "Le déclencheur passe en état PROBLEM."
    assert sheet.cell(4, 5).value == "RECOVERY"
    assert sheet.cell(4, 6).value == "{$CPU.MAX}=90\n{$CPU.RECOVERY}=80"
    assert sheet.cell(4, 9).value == "Le déclencheur revient à l'état OK."
    assert sheet.cell(3, 1).fill.fgColor.rgb == sheet.cell(4, 1).fill.fgColor.rgb
    assert sheet.cell(4, 1).font.bold is True
    assert sheet.row_dimensions[4].height == 42
    assert sheet.freeze_panes == "A3"


def test_generate_testbook_rejects_model_without_expected_headers(tmp_path: Path) -> None:
    model = tmp_path / "invalid.xlsx"
    workbook = Workbook()
    workbook.active.append(["Unknown", "Columns"])
    workbook.save(model)

    with pytest.raises(ValueError, match="expected header row"):
        generate_testbook(model, tmp_path / "output.xlsx", [])
