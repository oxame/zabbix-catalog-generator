"""Build test scenarios from parsed Zabbix probes."""

from __future__ import annotations

from pathlib import Path

from ..models import ProbeDefinition, TestCase


def build_test_cases(probes: list[ProbeDefinition]) -> list[TestCase]:
    """Create problem and recovery scenarios for enabled trigger definitions."""

    test_cases: list[TestCase] = []
    for probe in probes:
        for trigger in probe.triggers:
            test_cases.append(
                TestCase(
                    policy_name=probe.template_name,
                    resource=probe.name,
                    trigger_name=trigger.name,
                    severity=trigger.severity,
                    test_type="PROBLEM",
                    expected_result=f"Le déclencheur « {trigger.name} » passe en état PROBLEM.",
                )
            )
            if trigger.recovery_expression:
                test_cases.append(
                    TestCase(
                        policy_name=probe.template_name,
                        resource=probe.name,
                        trigger_name=trigger.name,
                        severity=trigger.severity,
                        test_type="RECOVERY",
                        expected_result=(
                            f"Le déclencheur « {trigger.name} » revient à l'état OK."
                        ),
                    )
                )
    return test_cases


def generate_testbook(
    model_path: str | Path,
    output_path: str | Path,
    test_cases: list[TestCase],
) -> Path:
    """Generate the test workbook from an Excel model.

    Excel population is implemented in Sprint 2. The explicit stub keeps the
    public API stable while preventing the creation of an incomplete workbook.
    """

    del model_path, output_path, test_cases
    raise NotImplementedError("Test workbook generation will be implemented in Sprint 2")
