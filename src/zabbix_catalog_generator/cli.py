from __future__ import annotations

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .excel import generate_catalogue
from .generators import build_test_cases, generate_testbook
from .parser import TemplateFormatError, load_active_probes


def _package_version() -> str:
    try:
        return version("zabbix-catalog-generator")
    except PackageNotFoundError:
        return "0.3.0"


def build_parser(*, command: str = "catalogue") -> argparse.ArgumentParser:
    if command == "tests":
        description = "Generate an Excel testbook from active Zabbix triggers."
        model_help = "Excel testbook model"
        output_help = "Generated testbook path"
    else:
        description = "Generate an Excel supervision catalogue from active Zabbix probes."
        model_help = "Excel catalogue model"
        output_help = "Generated catalogue path"

    parser = argparse.ArgumentParser(
        prog=f"zabbix-catalog {command}" if command != "catalogue" else "zabbix-catalog",
        description=description,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Zabbix Catalog Generator {_package_version()}",
    )
    parser.add_argument("template", type=Path, help="Zabbix YAML export")
    parser.add_argument("--model", required=True, type=Path, help=model_help)
    parser.add_argument("--output", type=Path, help=output_help)
    parser.add_argument("--sheet", help="Worksheet to populate (default: active worksheet)")
    return parser


def _step(message: str) -> None:
    print(f"[>] {message}", flush=True)


def _success(message: str) -> None:
    print(f"[OK] {message}", flush=True)


def _resolve_command(argv: list[str]) -> tuple[str, list[str]]:
    if argv and argv[0] in {"catalogue", "tests"}:
        return argv[0], argv[1:]
    return "catalogue", argv


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    command, command_argv = _resolve_command(raw_argv)
    args = build_parser(command=command).parse_args(command_argv)

    default_prefix = "Cahier_Test" if command == "tests" else "Catalogue"
    output = args.output or Path.cwd() / f"{default_prefix}_{args.template.stem}.xlsx"

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
        if command == "tests":
            test_cases = build_test_cases(probes)
            _step("Génération du cahier de tests")
            generate_testbook(
                args.model,
                output,
                test_cases,
                sheet_name=args.sheet,
            )
            _success(f"Cahier de tests généré ({len(test_cases)} scénarios)")
        else:
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
    label = "Cahier de tests" if command == "tests" else "Catalogue"
    print(f"{label:<23}: {output}")
    print("=" * 54)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
