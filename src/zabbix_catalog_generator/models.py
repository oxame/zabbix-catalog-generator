from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class TriggerDefinition:
    """An enabled Zabbix trigger associated with a monitoring item."""

    name: str
    expression: str = ""
    severity: str = "Not classified"
    description: str = ""
    recovery_expression: str = ""


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
    triggers: tuple[TriggerDefinition, ...] = field(default_factory=tuple)
