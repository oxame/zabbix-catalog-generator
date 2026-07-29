from __future__ import annotations

from dataclasses import dataclass, field

Tag = tuple[str, str]
Macro = tuple[str, str]


@dataclass(slots=True, frozen=True)
class TriggerDefinition:
    """An enabled Zabbix trigger associated with a monitoring item."""

    name: str
    expression: str = ""
    severity: str = "Not classified"
    description: str = ""
    recovery_expression: str = ""
    tags: tuple[Tag, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class ProbeDefinition:
    """An enabled Zabbix item or item prototype exported as a catalogue probe."""

    template_name: str
    template_description: str
    name: str
    key: str
    description: str
    delay: str
    item_type: str
    value_type: str
    units: str
    history: str
    trends: str
    lld: bool = False
    discovery_rule: str = ""
    dependency_keys: tuple[str, ...] = field(default_factory=tuple)
    dependency_names: tuple[str, ...] = field(default_factory=tuple)
    calculation_formula: str = ""
    preprocessing: tuple[str, ...] = field(default_factory=tuple)
    filters: tuple[str, ...] = field(default_factory=tuple)
    template_macros: tuple[Macro, ...] = field(default_factory=tuple)
    template_tags: tuple[Tag, ...] = field(default_factory=tuple)
    triggers: tuple[TriggerDefinition, ...] = field(default_factory=tuple)


@dataclass(slots=True, frozen=True)
class TestCase:
    """A test scenario generated from an enabled Zabbix trigger."""

    policy_name: str
    resource: str
    trigger_name: str
    severity: str
    test_type: str
    prerequisites: str = ""
    action: str = ""
    expected_result: str = ""
    comments: str = ""
