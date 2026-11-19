"""``pysos-sysml`` command line: validate a setup or emit its manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from pysos_sysml.loader import SysMLError, load_federation
from pysos_sysml.lower import manifest_json

__all__ = ["main"]


def _counts(federation) -> str:
    occurrences = sum(instance.count for instance in federation.instances)
    entities = sum(len(instance.entities) for instance in federation.instances)
    telemetry = sum(len(instance.telemetry_ports) for instance in federation.instances)
    control = sum(len(instance.control_ports) for instance in federation.instances)
    return "\n".join(
        [
            f"federation: {federation.name}",
            f"instances: {len(federation.instances)}",
            f"occurrences: {occurrences}",
            f"entities: {entities}",
            f"telemetry endpoints: {telemetry}",
            f"control endpoints: {control}",
        ]
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pysos-sysml",
        description=(
            "Validate a SysML system-of-systems setup or lower it to the "
            "schema-1 manifest owned by pysos_coordinate."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="parse and lower, then print counts")
    validate.add_argument("file", type=Path, help="setup .sysml file")

    manifest = commands.add_parser(
        "manifest", help="emit the schema-1 manifest owned by pysos_coordinate"
    )
    manifest.add_argument("file", type=Path, help="setup .sysml file")
    manifest.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write to this file instead of stdout",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        federation = load_federation(args.file)
    except SysMLError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.command == "validate":
        print(_counts(federation))
        return 0

    text = manifest_json(federation)
    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
