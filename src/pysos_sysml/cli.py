"""``pysos-sysml`` command line: validate a setup or emit its manifest."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path
from typing import Sequence

from pysos_sysml.loader import SysMLError, load_federation
from pysos_sysml.lower import manifest_json
from pysos_sysml.manifest import check, render

__all__ = ["main"]

MAX_DIFF_LINES = 20


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
    validate.add_argument(
        "--include",
        action="append",
        type=Path,
        default=[],
        metavar="PATH",
        help="include a vocabulary/architecture root (repeatable)",
    )

    manifest = commands.add_parser(
        "manifest", help="emit the schema-1 manifest owned by pysos_coordinate"
    )
    manifest.add_argument("file", type=Path, help="setup .sysml file")
    manifest.add_argument(
        "--include",
        action="append",
        type=Path,
        default=[],
        metavar="PATH",
        help="include a vocabulary/architecture root (repeatable)",
    )
    manifest.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write to this file instead of stdout",
    )
    manifest.add_argument(
        "--check",
        action="store_true",
        help="verify -o/--output is the current lowering; exit 1 on drift",
    )
    return parser


def _report_drift(
    setup: Path, expected_path: Path, *, includes: Sequence[Path | str] = ()
) -> None:
    try:
        expected = expected_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print(f"drift: {expected_path} is missing", file=sys.stderr)
        return
    print(f"drift: {expected_path} is not up to date", file=sys.stderr)
    diff = list(
        difflib.unified_diff(
            expected.splitlines(),
            render(setup, includes=includes).splitlines(),
            fromfile=str(expected_path),
            tofile="lowered",
            lineterm="",
        )
    )
    for line in diff[:MAX_DIFF_LINES]:
        print(line, file=sys.stderr)
    remaining = len(diff) - MAX_DIFF_LINES
    if remaining > 0:
        print(f"... {remaining} more diff lines", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "manifest" and args.check and args.output is None:
        parser.error("--check requires -o/--output")
    includes = tuple(args.include or ())
    try:
        if args.command == "validate":
            print(_counts(load_federation(args.file, includes=includes)))
            return 0
        if args.check:
            if check(args.file, args.output, includes=includes):
                print(f"ok: {args.output} is up to date")
                return 0
            _report_drift(args.file, args.output, includes=includes)
            return 1
        text = manifest_json(load_federation(args.file, includes=includes))
    except SysMLError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
