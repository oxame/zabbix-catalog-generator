from __future__ import annotations

from dataclasses import dataclass

from zabbix_catalog_generator.models import ProbeDefinition
from zabbix_catalog_generator.models import TestCase


def build_test_cases(
    probes: list[ProbeDefinition],
) -> list[TestCase]:
    """
    Build the list of test cases from probe definitions.

    For each trigger:
        - create one PROBLEM test
        - create one RECOVERY test when a recovery expression exists.
    """

    test_cases: list[TestCase] = []

    for probe in probes:
        resource = probe.name

        for trigger in probe.triggers:

            test_cases.append(
                TestCase(
                    policy_name=probe.template_name,
                    resource=resource,
                    trigger_name=trigger.name,
                    severity=trigger.severity,
                    test_type="PROBLEM",
                    expected_result=(
                        f'Trigger "{trigger.name}" '
                        f'changes to PROBLEM '
                        f'({trigger.severity}).'
                    ),
                )
            )

            if trigger.recovery_expression:

                test_cases.append(
                    TestCase(
                        policy_name=probe.template_name,
                        resource=resource,
                        trigger_name=trigger.name,
                        severity=trigger.severity,
                        test_type="RECOVERY",
                        expected_result=(
                            f'Trigger "{trigger.name}" '
                            "returns to OK."
                        ),
                    )
                )

    return test_cases
