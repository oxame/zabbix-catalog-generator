from pathlib import Path

from zabbix_catalog_generator.parser import load_active_probes


def test_only_enabled_items_rules_prototypes_and_triggers_are_loaded(tmp_path: Path) -> None:
    source = tmp_path / "template.yaml"
    source.write_text(
        """
zabbix_export:
  templates:
    - name: Demo
      items:
        - name: Active item
          key: demo.active
          delay: 5m
          triggers:
            - name: Active trigger
              expression: last(/Demo/demo.active)>0
              priority: HIGH
            - name: Disabled trigger
              status: DISABLED
        - name: Disabled item
          key: demo.disabled
          status: DISABLED
      discovery_rules:
        - name: Active discovery
          item_prototypes:
            - name: Active prototype {#NAME}
              key: demo.prototype[{#NAME}]
          trigger_prototypes:
            - name: Prototype trigger
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

    assert [probe.key for probe in probes] == ["demo.active", "demo.prototype[{#NAME}]"]
    assert [trigger.name for trigger in probes[0].triggers] == [
        "Active trigger",
        "Standalone trigger",
    ]
    assert probes[1].triggers[0].name == "Prototype trigger"
    assert probes[1].lld is True
    assert probes[1].discovery_rule == "Active discovery"
