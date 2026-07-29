from pathlib import Path

import pytest

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
        triggers=triggers,
    )


def test_test_case_defaults_are_empty() -> None:
    test_case = TestCase(
        policy_name="Template",
        resource="Resource",
        trigger_name="Trigger",
        severity="HIGH",
        test_type="PROBLEM",
    )

    assert test_case.prerequisites == ""
    assert test_case.action == ""
    assert test_case.expected_result == ""
    assert test_case.comments == ""


def test_build_test_cases_creates_problem_and_recovery_scenarios() -> None:
    trigger = TriggerDefinition(
        name="CPU usage is high",
        severity="HIGH",
        expression="last(/template/system.cpu.util)>90",
        recovery_expression="last(/template/system.cpu.util)<80",
    )

    test_cases = build_test_cases([_probe(trigger)])

    assert [test_case.test_type for test_case in test_cases] == ["PROBLEM", "RECOVERY"]
    assert all(test_case.policy_name == "Linux by Zabbix agent" for test_case in test_cases)
    assert all(test_case.resource == "CPU utilization" for test_case in test_cases)
    assert all(test_case.trigger_name == "CPU usage is high" for test_case in test_cases)
    assert all(test_case.severity == "HIGH" for test_case in test_cases)


def test_build_test_cases_skips_recovery_without_expression() -> None:
    trigger = TriggerDefinition(name="CPU usage is high", severity="WARNING")

    test_cases = build_test_cases([_probe(trigger)])

    assert len(test_cases) == 1
    assert test_cases[0].test_type == "PROBLEM"


def test_generators_package_keeps_catalogue_api() -> None:
    assert callable(generate_catalogue)


def test_generate_testbook_is_explicit_sprint_two_stub() -> None:
    with pytest.raises(NotImplementedError, match="Sprint 2"):
        generate_testbook(Path("model.xlsx"), Path("output.xlsx"), [])
