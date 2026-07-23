from __future__ import annotations

from dataclasses import dataclass
import re

from .models import ProbeDefinition


@dataclass(slots=True, frozen=True)
class EnrichedProbeFields:
    """Catalogue fields inferred from a Zabbix probe definition."""

    collection_method: str
    target_property: str
    resource_type: str
    category: str


COLLECTION_METHODS = {
    "ZABBIX_PASSIVE": "Agent Zabbix (passif)",
    "ZABBIX_ACTIVE": "Agent Zabbix (actif)",
    "SNMP_AGENT": "SNMP",
    "SNMP_TRAP": "Trap SNMP",
    "HTTP_AGENT": "HTTP/HTTPS",
    "SIMPLE": "Contrôle simple",
    "EXTERNAL": "Script externe",
    "ODBC": "ODBC",
    "JMX": "JMX",
    "IPMI": "IPMI",
    "SSH": "SSH",
    "TELNET": "Telnet",
    "TRAPPER": "Trapper Zabbix",
    "INTERNAL": "Interne Zabbix",
    "DEPENDENT": "Item dépendant",
    "CALCULATED": "Item calculé",
    "SCRIPT": "Script",
    "BROWSER": "Navigateur web",
}

TECHNOLOGY_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("oracle",), "Oracle"),
    (("mssql", "sql server", "sqlserver"), "Microsoft SQL Server"),
    (("mysql", "mariadb"), "MySQL/MariaDB"),
    (("postgresql", "postgres"), "PostgreSQL"),
    (("vmware", "vcenter", "esxi", "esx"), "VMware"),
    (("windows", "wmi"), "Windows"),
    (("linux",), "Linux"),
    (("apache",), "Apache HTTP Server"),
    (("nginx",), "Nginx"),
    (("iis",), "Microsoft IIS"),
    (("jmx", "java"), "Java/JMX"),
    (("certificate", "certificat", "x509"), "Certificat TLS"),
    (("http", "web", "url"), "Service web"),
    (("snmp",), "Équipement SNMP"),
)

RESOURCE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("oracle", "mssql", "sql server", "sqlserver", "mysql", "mariadb", "postgres"), "Base de données"),
    (("vmware", "vcenter", "esxi", "esx", "hypervisor"), "Virtualisation"),
    (("certificate", "certificat", "x509", "tls"), "Certificat"),
    (("http", "https", "web", "url"), "Service web"),
    (("net.if", "network", "interface", "icmp", "ping"), "Réseau"),
    (("vfs.fs", "filesystem", "file system", "disk", "volume"), "Système de fichiers"),
    (("service", "systemd"), "Service système"),
    (("process", "proc."), "Processus"),
    (("cpu", "memory", "mem", "swap", "system.uptime"), "Système"),
)

CATEGORY_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("available", "availability", "ping", "icmp", "status", "state", "health", "uptime"), "Disponibilité"),
    (("certificate", "certificat", "x509", "expiry", "expire"), "Sécurité"),
    (("free", "used", "usage", "utilization", "capacity", "space", "size", "tablespace"), "Capacité"),
    (("error", "failed", "failure", "problem", "alarm"), "Événement"),
    (("version", "inventory", "serial", "model", "name"), "Inventaire"),
    (("latency", "response", "performance", "load", "cpu", "memory", "sessions", "processes"), "Performance"),
)


def _search_text(probe: ProbeDefinition) -> str:
    return " ".join(
        (
            probe.template_name,
            probe.name,
            probe.key,
            probe.description,
            probe.discovery_rule,
        )
    ).casefold()


def _first_matching_rule(
    text: str,
    rules: tuple[tuple[tuple[str, ...], str], ...],
    default: str,
) -> str:
    for patterns, label in rules:
        if any(pattern.casefold() in text for pattern in patterns):
            return label
    return default


def infer_collection_method(probe: ProbeDefinition) -> str:
    """Translate a Zabbix item type into a catalogue collection method."""

    item_type = probe.item_type.upper()
    if item_type in COLLECTION_METHODS:
        return COLLECTION_METHODS[item_type]
    return re.sub(r"[_-]+", " ", item_type).strip().title() or "Non déterminé"


def enrich_probe(probe: ProbeDefinition) -> EnrichedProbeFields:
    """Infer catalogue metadata using stable built-in rules."""

    text = _search_text(probe)
    return EnrichedProbeFields(
        collection_method=infer_collection_method(probe),
        target_property=_first_matching_rule(text, TECHNOLOGY_RULES, "Générique"),
        resource_type=_first_matching_rule(text, RESOURCE_RULES, "Ressource supervisée"),
        category=_first_matching_rule(text, CATEGORY_RULES, "Métrologie"),
    )
