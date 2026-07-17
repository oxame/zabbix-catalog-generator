from zabbix_catalog_generator.enrichment import enrich_probe
from zabbix_catalog_generator.models import ProbeDefinition


def _probe(**overrides: object) -> ProbeDefinition:
    values: dict[str, object] = {
        "template_name": "Generic template",
        "template_description": "",
        "name": "Generic metric",
        "key": "generic.metric",
        "description": "",
        "delay": "5m",
        "item_type": "ZABBIX_ACTIVE",
        "value_type": "UNSIGNED",
        "units": "",
        "history": "7d",
        "trends": "365d",
    }
    values.update(overrides)
    return ProbeDefinition(**values)  # type: ignore[arg-type]


def test_oracle_agent_item_is_enriched() -> None:
    fields = enrich_probe(
        _probe(
            template_name="Oracle by Zabbix agent 2",
            name="Tablespace used percentage",
            key="oracle.tablespace.pctused[\"{#TABLESPACE}\"]",
        )
    )

    assert fields.collection_method == "Agent Zabbix (actif)"
    assert fields.target_property == "Oracle"
    assert fields.resource_type == "Base de données"
    assert fields.category == "Capacité"


def test_snmp_network_availability_is_enriched() -> None:
    fields = enrich_probe(
        _probe(
            template_name="Network device by SNMP",
            name="ICMP availability",
            key="icmpping",
            item_type="SIMPLE",
        )
    )

    assert fields.collection_method == "Contrôle simple"
    assert fields.target_property == "Équipement SNMP"
    assert fields.resource_type == "Réseau"
    assert fields.category == "Disponibilité"


def test_dependent_item_keeps_explicit_collection_method() -> None:
    fields = enrich_probe(
        _probe(
            template_name="Microsoft SQL Server",
            name="Sessions used",
            key="mssql.sessions.used",
            item_type="DEPENDENT",
        )
    )

    assert fields.collection_method == "Item dépendant"
    assert fields.target_property == "Microsoft SQL Server"
    assert fields.resource_type == "Base de données"
    assert fields.category == "Capacité"
