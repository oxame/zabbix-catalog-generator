from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from .models import Macro, ProbeDefinition, Tag, TriggerDefinition

ENABLED = "ENABLED"


class TemplateFormatError(ValueError):
    """Raised when the YAML file is not a supported Zabbix export."""


def _is_enabled(entity: dict[str, Any]) -> bool:
    return str(entity.get("status", ENABLED)).upper() == ENABLED


def _tags(raw: Iterable[dict[str, Any]] | None) -> tuple[Tag, ...]:
    return tuple(
        (str(tag.get("tag", "")), str(tag.get("value", "")))
        for tag in (raw or [])
        if tag.get("tag")
    )


def _macros(raw: Iterable[dict[str, Any]] | None) -> tuple[Macro, ...]:
    return tuple(
        (str(macro.get("macro", "")), str(macro.get("value", "")))
        for macro in (raw or [])
        if macro.get("macro")
    )


def _preprocessing_steps(raw: Iterable[dict[str, Any]] | None) -> tuple[str, ...]:
    steps: list[str] = []
    for step in raw or []:
        step_type = str(step.get("type", "")).replace("_", " ").strip()
        parameters = step.get("parameters", []) or []
        if not isinstance(parameters, list):
            parameters = [parameters]
        details = " ; ".join(str(parameter) for parameter in parameters if str(parameter))
        rendered = f"{step_type}: {details}" if details else step_type
        if rendered:
            steps.append(rendered)
    return tuple(steps)


def _discovery_filters(rule: dict[str, Any]) -> tuple[str, ...]:
    filter_definition = rule.get("filter") or {}
    conditions = filter_definition.get("conditions", []) or []
    rendered: list[str] = []
    for condition in conditions:
        macro = str(condition.get("macro", ""))
        operator = str(condition.get("operator", "MATCHES")).replace("_", " ").lower()
        value = str(condition.get("value", ""))
        formula_id = str(condition.get("formulaid", ""))
        prefix = f"{formula_id}: " if formula_id else ""
        text = " ".join(part for part in (macro, operator, value) if part)
        if text:
            rendered.append(f"{prefix}{text}")
    return tuple(rendered)


def _trigger_from_dict(trigger: dict[str, Any]) -> TriggerDefinition:
    return TriggerDefinition(
        name=str(trigger.get("name", "")),
        expression=str(trigger.get("expression", "")),
        severity=str(trigger.get("priority", "NOT_CLASSIFIED")),
        description=str(trigger.get("description", "")),
        recovery_expression=str(trigger.get("recovery_expression", "")),
        tags=_tags(trigger.get("tags")),
    )


def _enabled_triggers(raw: Iterable[dict[str, Any]] | None) -> tuple[TriggerDefinition, ...]:
    return tuple(_trigger_from_dict(trigger) for trigger in (raw or []) if _is_enabled(trigger))


def _item_triggers(item: dict[str, Any]) -> tuple[TriggerDefinition, ...]:
    """Read normal triggers and trigger prototypes embedded in an item definition."""

    raw_triggers = [
        *(item.get("triggers", []) or []),
        *(item.get("trigger_prototypes", []) or []),
    ]
    return _enabled_triggers(raw_triggers)


def _master_item_key(item: dict[str, Any]) -> str:
    master_item = item.get("master_item")
    if isinstance(master_item, dict):
        return str(master_item.get("key", ""))
    return ""


def _probe_from_item(
    item: dict[str, Any],
    *,
    template_name: str,
    template_description: str,
    template_macros: tuple[Macro, ...],
    template_tags: tuple[Tag, ...],
    lld: bool = False,
    discovery_rule: str = "",
    filters: tuple[str, ...] = (),
) -> ProbeDefinition:
    master_key = _master_item_key(item)
    return ProbeDefinition(
        template_name=template_name,
        template_description=template_description,
        name=str(item.get("name", "")),
        key=str(item.get("key", "")),
        description=str(item.get("description", "")),
        delay=str(item.get("delay", "")),
        item_type=str(item.get("type", "ZABBIX_PASSIVE")),
        value_type=str(item.get("value_type", "UNSIGNED")),
        units=str(item.get("units", "")),
        history=str(item.get("history", "")),
        trends=str(item.get("trends", "")),
        lld=lld,
        discovery_rule=discovery_rule,
        dependency_keys=(master_key,) if master_key else (),
        calculation_formula=str(item.get("params", "")),
        preprocessing=_preprocessing_steps(item.get("preprocessing")),
        filters=filters,
        template_macros=template_macros,
        template_tags=template_tags,
        triggers=_item_triggers(item),
    )


def _attach_triggers(
    probes: list[ProbeDefinition], raw_triggers: Iterable[dict[str, Any]] | None
) -> list[ProbeDefinition]:
    """Attach each active standalone trigger to its first referenced active probe."""

    result = list(probes)
    for raw_trigger in raw_triggers or []:
        if not _is_enabled(raw_trigger):
            continue
        expression = str(raw_trigger.get("expression", ""))
        referenced = [
            (expression.find(probe.key), index)
            for index, probe in enumerate(result)
            if probe.key and expression.find(probe.key) >= 0
        ]
        if not referenced:
            continue
        _, index = min(referenced)
        trigger = _trigger_from_dict(raw_trigger)
        result[index] = replace(result[index], triggers=(*result[index].triggers, trigger))
    return result


def _resolve_dependencies(probes: list[ProbeDefinition]) -> list[ProbeDefinition]:
    """Resolve dependency keys to item names, including calculated item formulas."""

    key_to_name = {probe.key: probe.name for probe in probes if probe.key}
    known_keys = sorted(key_to_name, key=len, reverse=True)
    resolved: list[ProbeDefinition] = []

    for probe in probes:
        dependency_keys = list(probe.dependency_keys)
        if probe.item_type.upper() == "CALCULATED" and probe.calculation_formula:
            for candidate in known_keys:
                if candidate != probe.key and candidate in probe.calculation_formula:
                    dependency_keys.append(candidate)

        unique_keys = tuple(dict.fromkeys(key for key in dependency_keys if key))
        dependency_names = tuple(
            dict.fromkeys(key_to_name[key] for key in unique_keys if key in key_to_name)
        )
        resolved.append(
            replace(
                probe,
                dependency_keys=unique_keys,
                dependency_names=dependency_names,
            )
        )

    return resolved


def load_active_probes(path: str | Path) -> list[ProbeDefinition]:
    """Load enabled items and enabled LLD item prototypes from a Zabbix YAML export."""

    source = Path(path)
    with source.open("r", encoding="utf-8") as stream:
        document = yaml.safe_load(stream)

    try:
        templates = document["zabbix_export"]["templates"]
    except (TypeError, KeyError) as exc:
        raise TemplateFormatError(
            f"{source} is not a supported Zabbix YAML export: templates are missing"
        ) from exc

    probes: list[ProbeDefinition] = []
    for template in templates:
        if not _is_enabled(template):
            continue

        template_name = str(template.get("name") or template.get("template") or "")
        template_description = str(template.get("description", ""))
        template_macros = _macros(template.get("macros"))
        template_tags = _tags(template.get("tags"))

        for item in template.get("items", []) or []:
            if _is_enabled(item):
                probes.append(
                    _probe_from_item(
                        item,
                        template_name=template_name,
                        template_description=template_description,
                        template_macros=template_macros,
                        template_tags=template_tags,
                    )
                )

        for rule in template.get("discovery_rules", []) or []:
            if not _is_enabled(rule):
                continue
            rule_name = str(rule.get("name", ""))
            filters = _discovery_filters(rule)
            rule_probes: list[ProbeDefinition] = []
            for prototype in rule.get("item_prototypes", []) or []:
                if _is_enabled(prototype):
                    rule_probes.append(
                        _probe_from_item(
                            prototype,
                            template_name=template_name,
                            template_description=template_description,
                            template_macros=template_macros,
                            template_tags=template_tags,
                            lld=True,
                            discovery_rule=rule_name,
                            filters=filters,
                        )
                    )
            probes.extend(_attach_triggers(rule_probes, rule.get("trigger_prototypes")))

    probes = _attach_triggers(probes, document["zabbix_export"].get("triggers"))
    return _resolve_dependencies(probes)
