from pathlib import Path

from zabbix_catalog_generator.parser import load_active_probes


def test_only_enabled_items_rules_prototypes_and_triggers_are_loaded(tmp_path: Path) -> None:
    source = tmp_path / "template.yaml"
    source.write_text(
        """
zabbix_export:
  templates:
    - name: Demo
      macros:
        - macro: '{$CPU.MAX}'
          value: '90'
      tags:
        - tag: component
          value: demo
      items:
        - name: Raw value
          key: demo.raw
          delay: 1m
        - name: Active item {$CPU.MAX}
          key: demo.active
          delay: 5m
          preprocessing:
            - type: JSONPATH
              parameters:
                - $.value
          triggers:
            - name: Active trigger
              expression: last(/Demo/demo.active)>{$CPU.MAX}
              priority: HIGH
              tags:
                - tag: scope
                  value: performance
            - name: Disabled trigger
              status: DISABLED
        - name: Dependent item
          key: demo.dependent
          type: DEPENDENT
          master_item:
            key: demo.raw
        - name: Calculated item
          key: demo.calculated
          type: CALCULATED
          params: last(//demo.active) + last(//demo.raw)
        - name: Disabled item
          key: demo.disabled
          status: DISABLED
      discovery_rules:
        - name: Active discovery
          filter:
            conditions:
              - macro: '{#NAME}'
                operator: MATCHES_REGEX
                value: ^eth
                formulaid: A
          item_prototypes:
            - name: Active prototype {#NAME}
              key: demo.prototype[{#NAME}]
              trigger_prototypes:
                - name: Nested prototype trigger
                  expression: last(/Demo/demo.prototype[{#NAME}])>1
                  priority: AVERAGE
                - name: Disabled nested prototype trigger
                  expression: last(/Demo/demo.prototype[{#NAME}])>2
                  status: DISABLED
          trigger_prototypes:
            - name: Rule-level prototype trigger
              expression: last(/Demo/demo.prototype[{#NAME}])>0
        - name: Disabled discovery
          status: DISABLED
          item_prototypes:
            - name: Hidden prototype
              key: hidden
  triggers:
    - name: Standalone trigger
      expression: last(/Demo/demo.active)>0
      priority: WARNING
""",
        encoding="utf-8",
    )

    probes = load_active_probes(source)

    assert [probe.key for probe in probes] == [
        "demo.raw",
        "demo.active",
        "demo.dependent",
        "demo.calculated",
        "demo.prototype[{#NAME}]",
    ]
    assert [trigger.name for trigger in probes[1].triggers] == [
        "Active trigger",
        "Standalone trigger",
    ]
    assert probes[1].preprocessing == ("JSONPATH: $.value",)
    assert probes[1].template_macros == (("{$CPU.MAX}", "90"),)
    assert probes[1].template_tags == (("component", "demo"),)
    assert probes[1].triggers[0].tags == (("scope", "performance"),)
    assert probes[2].dependency_names == ("Raw value",)
    assert probes[3].dependency_names == ("Active item {$CPU.MAX}", "Raw value")
    assert [trigger.name for trigger in probes[4].triggers] == [
        "Nested prototype trigger",
        "Rule-level prototype trigger",
    ]
    assert probes[4].triggers[0].severity == "AVERAGE"
    assert probes[4].lld is True
    assert probes[4].discovery_rule == "Active discovery"
    assert probes[4].filters == ("A: {#NAME} matches regex ^eth",)
