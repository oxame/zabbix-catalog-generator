from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .excel import generate_catalogue
from .parser import TemplateFormatError, load_active_probes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zabbix-catalog",
        description="Generate an Excel supervision catalogue from active Zabbix probes.",
    )
    parser.add_argument("template", type=Path, help="Zabbix YAML export")
    parser.add_argument("--model", required=True, type=Path, help="Excel catalogue model")
    parser.add_argument("--output", type=Path, help="Generated catalogue path")
    parser.add_argument("--sheet", help="Worksheet to populate (default: active worksheet)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = args.output or Path.cwd() / f"Catalogue_{args.template.stem}.xlsx"

    try:
        probes = load_active_probes(args.template)
        generate_catalogue(args.model, output, probes, sheet_name=args.sheet)
    except (OSError, ValueError, TemplateFormatError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    trigger_count = sum(len(probe.triggers) for probe in probes)
    lld_count = sum(1 for probe in probes if probe.lld)
    print(f"Catalogue generated: {output}")
    print(f"Active probes: {len(probes)} (including {lld_count} LLD prototypes)")
    print(f"Active triggers attached to probes: {trigger_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
