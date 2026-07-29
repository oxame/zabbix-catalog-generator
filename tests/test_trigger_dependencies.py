from pathlib import Path

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


def test_dependency_scenario_is_generated_and_parent_names_are_rendered(tmp_path: Path) -> None:
    repository = tmp_path / "scenarios.yaml"
    repository.write_text(
        """
- code: TEST-TRG-007
  title: Dépendance entre déclencheurs
  applies: dependencies
  objective: Vérifier les dépendances de ${trigger.name}.
  procedure: |-
    Déclencheurs parents :
    ${trigger.dependencies}
  expected_result: Le déclencheur dépendant est inhibé.
""".strip(),
        encoding="utf-8",
    )
    independent = TriggerDefinition(name="Independent", expression="last(/Demo/app.status)=0")
    dependent = TriggerDefinition(
        name="Application unavailable",
        expression="last(/Demo/app.status)=0",
        dependencies=("Server unavailable", "Network unavailable"),
    )

    test_cases = build_test_cases(
        [_probe(independent, dependent)],
        scenarios_path=repository,
    )

    assert len(test_cases) == 1
    assert test_cases[0].trigger_name == "Application unavailable"
    assert test_cases[0].test_code == "TEST-TRG-007"
    assert "Server unavailable\nNetwork unavailable" in test_cases[0].procedure
    assert "${" not in test_cases[0].procedure
