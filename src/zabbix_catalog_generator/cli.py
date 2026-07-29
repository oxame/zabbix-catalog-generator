from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .excel import generate_catalogue
from .parser import TemplateFormatError, load_active_probes


def _package_version() -> str:
    try:
        return version("zabbix-catalog-generator")
    except PackageNotFoundError:
        return "0.2.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zabbix-catalog",
        description="Generate an Excel supervision catalogue from active Zabbix probes.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Zabbix Catalog Generator {_package_version()}",
    )
    parser.add_argument("template", type=Path, help="Zabbix YAML export")
    parser.add_argument("--model", required=True, type=Path, help="Excel catalogue model")
    parser.add_argument("--output", type=Path, help="Generated catalogue path")
    parser.add_argument("--sheet", help="Worksheet to populate (default: active worksheet)")
    return parser


def _step(message: str) -> None:
    print(f"[>] {message}", flush=True)


def _success(message: str) -> None:
    print(f"[OK] {message}", flush=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output or Path.cwd() / f"Catalogue_{args.template.stem}.xlsx"

    print("=" * 54)
    print(" Zabbix Catalog Generator")
    print("=" * 54)

    try:
        _step(f"Lecture du template : {args.template}")
        probes = load_active_probes(args.template)
        _success(f"{len(probes)} sondes actives trouvées")

        dependent_count = sum(1 for probe in probes if probe.dependency_names)
        if dependent_count:
            _success(f"{dependent_count} sondes dépendantes ou calculées identifiées")

        _step(f"Chargement du modèle Excel : {args.model}")
        _step("Génération du catalogue")
        generate_catalogue(args.model, output, probes, sheet_name=args.sheet)
        _success("Catalogue Excel généré")
    except (OSError, ValueError, TemplateFormatError) as exc:
        print(f"[ERREUR] {exc}", file=sys.stderr)
        return 1

    trigger_count = sum(len(probe.triggers) for probe in probes)
    lld_count = sum(1 for probe in probes if probe.lld)

    print("-" * 54)
    print(f"Sondes actives          : {len(probes)}")
    print(f"Prototypes LLD          : {lld_count}")
    print(f"Déclencheurs actifs     : {trigger_count}")
    print(f"Catalogue               : {output}")
    print("=" * 54)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
