from zabbix_catalog_generator.generators import build_test_cases
from zabbix_catalog_generator.models import ProbeDefinition, TriggerDefinition


def _probe(*triggers: TriggerDefinition) -> ProbeDefinition:
    return ProbeDefinition(
        template_name="Demo",
        template_description="",
        name="Application status",
        key="app.status",
        description="",
        delay="1m",
        item_type="ZABBIX_PASSIVE",
        value_type="UNSIGNED",
        units="",
        history="7d",
        trends="365d",
        triggers=triggers,
    )


def test_dependency_scenario_is_generated_and_parent_names_are_rendered() -> None:
    independent = TriggerDefinition(name="Independent", expression="last(/Demo/app.status)=0")
    dependent = TriggerDefinition(
        name="Application unavailable",
        expression="last(/Demo/app.status)=0",
        dependencies=("Server unavailable", "Network unavailable"),
    )

    test_cases = build_test_cases([_probe(independent, dependent)])
    dependency_cases = [case for case in test_cases if case.test_code == "TEST-TRG-007"]

    assert len(dependency_cases) == 1
    test_case = dependency_cases[0]
    assert test_case.trigger_name == "Application unavailable"
    assert "Server unavailable\nNetwork unavailable" in test_case.prerequisites
    assert "Server unavailable\nNetwork unavailable" in test_case.procedure
    assert "Application unavailable" in test_case.procedure
    assert "${" not in test_case.prerequisites
    assert "${" not in test_case.procedure
