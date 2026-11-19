"""Load the supported SysML subset into :mod:`pysos_sysml.model`.

Parsing is delegated wholesale to ``pycps_sysml2.load``. This module only
walks the repo-owned ``Architecture`` model and rejects everything the subset
does not define. The one exception is part-usage multiplicity: ``pycps_sysml2``
0.2.0 does not retain it on ``PartUsage`` (see
``docs/breakdown/02-architecture/layers.md``), so :func:`_multiplicities`
reads the single-line ``[N]`` annotation lexically. Structure, names, types,
and attribute values still come from the parser.

Nothing here ignores an input: every unsupported definition, usage, member,
attribute, or value raises :class:`SysMLError` with the offending qualified
name and the source path.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pycps_sysml2

from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef

__all__ = ["SysMLError", "load_federation"]

_FEDERATION_DEF = "Federation"

_INTEGER_ATTRIBUTES = (
    "site",
    "application",
    "entity",
    "telemetryPort",
    "controlPort",
)
_STRING_ATTRIBUTES = ("marking", "command", "cwd")
_INSTANCE_ATTRIBUTES = _INTEGER_ATTRIBUTES + _STRING_ATTRIBUTES
_ATTRIBUTE_TYPES = {
    **{name: "Integer" for name in _INTEGER_ATTRIBUTES},
    **{name: "String" for name in _STRING_ATTRIBUTES},
}

# A part usage multiplicity is only an integer occurrence count in this subset.
# The match is anchored to one physical line: the lexical adjunct reads the
# annotation the parser drops, it is not a general SysML reader.
_MULTIPLICITY = re.compile(
    r"^\s*part\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"\s*:\s*(?P<type>[A-Za-z_][A-Za-z0-9_:]*)"
    r"\s*\[\s*(?P<count>[^\]]*?)\s*\]"
)
_INTEGER_LITERAL = re.compile(r"[+-]?\d+")


class SysMLError(ValueError):
    """The input is outside the supported SysML subset or cannot be parsed."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else None
        super().__init__(f"{self.path}: {message}" if self.path else message)


def _error(path: Path, qualified: str, message: str) -> SysMLError:
    return SysMLError(f"{qualified}: {message}", path=path)


def _integer_literal(value: Any, *, path: Path, qualified: str) -> int:
    if isinstance(value, bool):
        raise _error(path, qualified, "expected an Integer literal")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _INTEGER_LITERAL.fullmatch(value.strip()):
        return int(value.strip())
    raise _error(path, qualified, f"expected an Integer literal, got {value!r}")


def _string_literal(value: Any, *, path: Path, qualified: str) -> str:
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            parsed = None
        if isinstance(parsed, str):
            return parsed
    raise _error(path, qualified, f"expected a quoted String literal, got {value!r}")


def _attribute_value(attribute: Any, expected: str, *, path: Path, qualified: str) -> int | str:
    if attribute.type_name is None:
        raise _error(path, qualified, "attribute has no declared type")
    if attribute.type_name != expected:
        raise _error(
            path,
            qualified,
            f"attribute must be typed {expected}, got {attribute.type_name}",
        )
    if attribute.value is None:
        raise _error(path, qualified, "attribute has no literal value")
    if expected == "Integer":
        return _integer_literal(attribute.value, path=path, qualified=qualified)
    return _string_literal(attribute.value, path=path, qualified=qualified)


def _multiplicities(path: Path, package: str) -> dict[str, tuple[str, int]]:
    """Part-usage occurrence counts written as ``part name : Type [N]``.

    Only the dropped multiplicity is recovered here; the parser remains the
    authority on which usages exist and what they are typed by.
    """
    found: dict[str, tuple[str, int]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SysMLError(f"cannot read model: {exc}", path=path) from exc

    for line in lines:
        match = _MULTIPLICITY.match(line)
        if match is None:
            continue
        name = match.group("name")
        type_name = match.group("type")
        raw = match.group("count")
        qualified = f"{package}::{_FEDERATION_DEF}::{name}[{raw}]"
        if not raw.isdigit() or int(raw) < 1:
            raise _error(
                path,
                qualified,
                "part multiplicity must be a positive integer, e.g. [3]",
            )
        count = int(raw)
        previous = found.get(name)
        if previous is not None and previous != (type_name, count):
            raise _error(
                path,
                qualified,
                f"conflicting multiplicities for part '{name}'",
            )
        found[name] = (type_name, count)
    return found


def _check_part_definition(part_def: Any, *, package: str, path: Path) -> None:
    qualified = f"{package}::{part_def.name}"
    if part_def.specializes:
        raise _error(path, qualified, "specialization is outside the subset")
    if part_def.is_variation or part_def.variants:
        raise _error(path, qualified, "variation is outside the subset")
    for kind, members in (
        ("attribute", part_def.attributes),
        ("port", part_def.ports),
        ("part", part_def.parts),
        ("connection", part_def.connections),
        ("binding", part_def.bindings),
        ("constraint", part_def.constraints),
    ):
        for name in members:
            raise _error(
                path,
                f"{qualified}::{name}",
                f"{kind} is outside the supported SysML subset",
            )


def _check_federation_definition(part_def: Any, *, package: str, path: Path) -> None:
    qualified = f"{package}::{part_def.name}"
    if part_def.specializes:
        raise _error(path, qualified, "specialization is outside the subset")
    if part_def.is_variation or part_def.variants:
        raise _error(path, qualified, "variation is outside the subset")
    for kind, members in (
        ("attribute", part_def.attributes),
        ("port", part_def.ports),
        ("connection", part_def.connections),
        ("binding", part_def.bindings),
        ("constraint", part_def.constraints),
    ):
        for name in members:
            raise _error(
                path,
                f"{qualified}::{name}",
                f"{kind} on Federation is outside the supported SysML subset",
            )


def _load_instance(
    usage: Any,
    *,
    architecture: Any,
    package: str,
    path: Path,
    counts: dict[str, tuple[str, int]],
) -> InstanceDef:
    qualified = f"{package}::{_FEDERATION_DEF}::{usage.name}"
    if usage.type_name is None:
        raise _error(path, qualified, "part usage has no declared type")
    if usage.is_variation or usage.variants:
        raise _error(path, qualified, "variation is outside the subset")
    if usage.redefines or usage.subsets or usage.value is not None:
        raise _error(path, qualified, "usage specialization is outside the subset")

    part_def = architecture.resolve_part(usage)
    if part_def is None:
        raise _error(
            path,
            qualified,
            f"unknown part definition '{usage.type_name}'",
        )

    body = usage.body
    if body is None:
        raise _error(path, qualified, "part usage has no attribute body")
    for kind, members in (
        ("part", body.parts),
        ("connection", body.connections),
        ("binding", body.bindings),
    ):
        for name in members:
            raise _error(
                path,
                f"{qualified}::{name}",
                f"{kind} inside a Federation instance is outside the subset",
            )

    attributes = body.attributes
    for name in attributes:
        if name not in _ATTRIBUTE_TYPES:
            raise _error(
                path,
                f"{qualified}::{name}",
                "attribute is outside the supported SysML subset",
            )
    values: dict[str, int | str] = {}
    for name in _INSTANCE_ATTRIBUTES:
        attribute = attributes.get(name)
        if attribute is None:
            raise _error(
                path,
                qualified,
                f"missing required attribute '{name}'",
            )
        values[name] = _attribute_value(
            attribute,
            _ATTRIBUTE_TYPES[name],
            path=path,
            qualified=f"{qualified}::{name}",
        )

    annotation = counts.get(usage.name)
    if annotation is not None:
        annotated_type, count = annotation
        if annotated_type != usage.type_name:
            raise _error(
                path,
                qualified,
                f"multiplicity annotation names type '{annotated_type}' "
                f"but the parser resolved '{usage.type_name}'",
            )
    else:
        count = 1

    site = int(values["site"])
    application = int(values["application"])
    entity = int(values["entity"])
    marking = str(values["marking"])
    telemetry = int(values["telemetryPort"])
    control = int(values["controlPort"])

    return InstanceDef(
        name=usage.name,
        part_def=part_def.name,
        count=count,
        entities=[
            EntityDef(
                site=site,
                application=application,
                entity=entity + index,
                marking=marking,
            )
            for index in range(count)
        ],
        telemetry_ports=[
            EndpointDef(name="telemetry", port=telemetry + index) for index in range(count)
        ],
        control_ports=[EndpointDef(name="control", port=control + index) for index in range(count)],
        command=str(values["command"]),
        cwd=str(values["cwd"]),
    )


def load_federation(path: Path | str) -> FederationDef:
    """Parse *path* and return the federation setup it declares.

    The supported subset is one ``package`` holding ``part def Federation``
    and the part definitions it uses; see
    ``docs/breakdown/02-architecture/sysml-subset.md``. Anything else raises
    :class:`SysMLError` naming the offender.
    """
    path = Path(path)
    try:
        architecture = pycps_sysml2.load(path)
    except Exception as exc:  # parser errors carry no qualified name
        raise SysMLError(f"cannot parse model: {exc}", path=path) from exc

    package = architecture.package_name
    if not package:
        raise SysMLError("model declares no package", path=path)
    if architecture.imports:
        raise _error(
            path,
            package,
            "imports are outside the subset; one package per model",
        )
    for key in architecture.included_definitions:
        raise _error(path, key, "included roots are outside the subset")

    for kind, definitions in (
        ("port def", architecture.port_definitions),
        ("attribute def", architecture.attribute_definitions),
        ("requirement def", architecture.requirement_definitions),
        ("constraint def", architecture.constraint_definitions),
    ):
        for key in definitions:
            raise _error(
                path,
                key if "::" in key else f"{package}::{key}",
                f"{kind} is outside the supported SysML subset",
            )

    federation = architecture.part_definitions.get(
        _FEDERATION_DEF
    ) or architecture.part_definitions.get(f"{package}::{_FEDERATION_DEF}")
    if federation is None:
        raise _error(
            path,
            f"{package}::{_FEDERATION_DEF}",
            f"missing 'part def {_FEDERATION_DEF}'",
        )

    for part_def in architecture.part_definitions.values():
        if part_def is federation:
            continue
        _check_part_definition(part_def, package=package, path=path)

    _check_federation_definition(federation, package=package, path=path)
    if not federation.parts:
        raise _error(
            path,
            f"{package}::{_FEDERATION_DEF}",
            "Federation declares no part instances",
        )

    counts = _multiplicities(path, package)
    instances: list[InstanceDef] = []
    for usage in federation.parts.values():
        instances.append(
            _load_instance(
                usage,
                architecture=architecture,
                package=package,
                path=path,
                counts=counts,
            )
        )

    instance_names = {instance.name for instance in instances}
    for name, (type_name, _count) in counts.items():
        if name not in instance_names:
            raise _error(
                path,
                f"{package}::{_FEDERATION_DEF}::{name}",
                f"multiplicity annotation names an unknown part usage typed '{type_name}'",
            )

    return FederationDef(
        name=package,
        instances=instances,
        metadata={
            "package": package,
            "definition": _FEDERATION_DEF,
            "source": path.name,
        },
    )
