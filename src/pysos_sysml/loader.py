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
from collections.abc import Sequence
from importlib import resources
from pathlib import Path
from typing import Any

import pycps_sysml2

from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef, LaunchDef

__all__ = ["SOS_FILE", "SysMLError", "load_federation", "sos_definitions"]

_FEDERATION_DEF = "Federation"

#: Name of the bundled system-of-systems launch vocabulary inside the package.
SOS_FILE = "sos.sysml"

_INTEGER_ATTRIBUTES = (
    "site",
    "application",
    "entity",
    "telemetryPort",
    "controlPort",
)
_STRING_ATTRIBUTES = ("marking", "command", "cwd")
_INSTANCE_ATTRIBUTES = _INTEGER_ATTRIBUTES + _STRING_ATTRIBUTES
_OPTIONAL_STRING_ATTRIBUTES = ("scenario",)
_ATTRIBUTE_TYPES = {
    **{name: "Integer" for name in _INTEGER_ATTRIBUTES},
    **{name: "String" for name in _STRING_ATTRIBUTES},
    **{name: "String" for name in _OPTIONAL_STRING_ATTRIBUTES},
}

_LAUNCH = "launch"
_LAUNCH_DEF = "LaunchSpec"
_LAUNCH_ATTRIBUTE_TYPES = {
    "mode": "String",
    "readiness": "String",
    "timeout_s": "Real",
    "order": "Integer",
    "after_process": "String",
}
_LAUNCH_MODES = frozenset({"supervised", "operator", "manual"})
_LAUNCH_READINESS = frozenset({"none", "port_bound", "log_line"})
_LAUNCH_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# A part usage multiplicity is only an integer occurrence count in this subset.
# The match is anchored to one physical line: the lexical adjunct reads the
# annotation the parser drops, it is not a general SysML reader.
_MULTIPLICITY = re.compile(
    r"^\s*part\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"\s*:\s*(?P<type>[A-Za-z_][A-Za-z0-9_:]*)"
    r"\s*\[\s*(?P<count>[^\]]*?)\s*\]"
)
_INTEGER_LITERAL = re.compile(r"[+-]?\d+")

# Duplicate launch attributes are collapsed by the parser's body dict. The
# validation adjunct below reads only the authored Federation body to recover
# the repeated names; it is not a second grammar.
_FEDERATION_BLOCK = re.compile(r"\bpart\s+def\s+Federation\s*\{")
_INSTANCE_BLOCK = re.compile(
    r"\bpart\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*[A-Za-z_][A-Za-z0-9_:]*"
    r"\s*(?:\[[^\]]*\])?\s*\{"
)
_LAUNCH_BLOCK = re.compile(r"\bpart\s+launch\s*:\s*[A-Za-z_][A-Za-z0-9_:]*\s*\{")
_LAUNCH_ATTRIBUTE = re.compile(r"\battribute\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:")


class SysMLError(ValueError):
    """The input is outside the supported SysML subset or cannot be parsed."""

    def __init__(self, message: str, *, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else None
        super().__init__(f"{self.path}: {message}" if self.path else message)


def sos_definitions() -> Path:
    """Return the bundled ``PysosSoS`` vocabulary as a real file path.

    The file is package data. An unpacked install yields a real ``Path``; a
    zipped install cannot expose one and is refused rather than handing a
    non-path to the parser.
    """
    path = resources.files(__package__).joinpath(SOS_FILE)
    if not isinstance(path, Path):
        raise RuntimeError(
            "pysos-sysml must be installed as an unpacked directory so the "
            "bundled system-of-systems definitions have a real file path"
        )
    if not path.is_file():
        raise FileNotFoundError(
            f"no system-of-systems definitions found at {path}; "
            "reinstall pysos-sysml"
        )
    return path


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


def _real_literal(value: Any, *, path: Path, qualified: str) -> float:
    if isinstance(value, bool):
        raise _error(path, qualified, "expected a Real literal")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            pass
    raise _error(path, qualified, f"expected a Real literal, got {value!r}")


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
    if expected == "Real":
        return _real_literal(attribute.value, path=path, qualified=qualified)
    return _string_literal(attribute.value, path=path, qualified=qualified)


def _resolve_part(
    architecture: Any, usage: Any, *, path: Path, qualified: str
) -> Any:
    """Resolve a part usage, turning the parser's visibility error into ours."""
    try:
        definition = architecture.resolve_part(usage)
    except ValueError as exc:
        raise _error(path, qualified, str(exc)) from exc
    if definition is None:
        raise _error(
            path,
            qualified,
            f"unknown part definition '{usage.type_name}'",
        )
    return definition


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


def _matching_brace(text: str, open_index: int) -> int:
    """Index of the ``}`` matching the ``{`` at *open_index*, or ``-1``.

    Quoted strings and comments are skipped so braces in authored text do not
    move the block boundary.
    """
    depth = 0
    index = open_index
    quote: str | None = None
    escaped = False
    while index < len(text):
        char = text[index]
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif text.startswith("//", index):
            newline = text.find("\n", index)
            if newline < 0:
                return -1
            index = newline
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                return -1
            index = end + 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _launch_duplicates(path: Path) -> dict[str, tuple[str, ...]]:
    """Repeated ``launch`` attribute names per authored instance.

    ``pycps_sysml2`` stores body attributes in a dict, so a repeated name
    silently keeps the last value. This validation adjunct reads only the
    primary ``Federation`` body to recover the names the parser collapsed; the
    parser remains the authority on every value.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    found = {}
    federation = _FEDERATION_BLOCK.search(text)
    if federation is None:
        return found
    close = _matching_brace(text, federation.end() - 1)
    if close < 0:
        return found
    body = text[federation.end() : close]

    cursor = 0
    while (instance := _INSTANCE_BLOCK.search(body, cursor)) is not None:
        instance_close = _matching_brace(body, instance.end() - 1)
        if instance_close < 0:
            break
        instance_body = body[instance.end() : instance_close]
        launch_cursor = 0
        while (launch := _LAUNCH_BLOCK.search(instance_body, launch_cursor)) is not None:
            launch_close = _matching_brace(instance_body, launch.end() - 1)
            if launch_close < 0:
                break
            launch_body = instance_body[launch.end() : launch_close]
            names = [
                match.group("name") for match in _LAUNCH_ATTRIBUTE.finditer(launch_body)
            ]
            repeated = tuple(sorted({name for name in names if names.count(name) > 1}))
            if repeated:
                found[instance.group("name")] = repeated
            launch_cursor = launch_close + 1
        cursor = instance_close + 1
    return found


def _check_entity_definition(
    part_def: Any, *, architecture: Any, package: str, path: Path
) -> None:
    """A primary non-Federation composition: only typed ``part`` usages."""
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
                f"{kind} is outside the supported SysML subset",
            )
    for name, usage in part_def.parts.items():
        nested = f"{qualified}::{name}"
        if usage.is_variation or usage.variants:
            raise _error(path, nested, "variation is outside the subset")
        if usage.redefines or usage.subsets or usage.value is not None:
            raise _error(path, nested, "usage specialization is outside the subset")
        if usage.body is not None:
            raise _error(path, nested, "a part usage body is outside the subset")
        if usage.type_name is None:
            raise _error(path, nested, "part usage has no declared type")
        _resolve_part(architecture, usage, path=path, qualified=nested)


def _check_launch_definition(definition: Any, *, path: Path, qualified: str) -> None:
    """The resolved launch vocabulary must be exactly the shipped shape."""
    if definition.name != _LAUNCH_DEF:
        raise _error(
            path,
            qualified,
            f"launch must resolve to a part def named '{_LAUNCH_DEF}', "
            f"got '{definition.name}'",
        )
    if definition.specializes:
        raise _error(path, qualified, "launch definition must not specialize")
    if definition.is_variation or definition.variants:
        raise _error(path, qualified, "launch definition must not be a variation")
    for kind, members in (
        ("part", definition.parts),
        ("port", definition.ports),
        ("connection", definition.connections),
        ("binding", definition.bindings),
        ("constraint", definition.constraints),
    ):
        if members:
            raise _error(
                path,
                qualified,
                f"launch definition declares a {kind}, which is outside the subset",
            )
    declared = set(definition.attributes)
    expected = set(_LAUNCH_ATTRIBUTE_TYPES)
    if declared != expected:
        missing = ", ".join(sorted(expected - declared)) or "none"
        extra = ", ".join(sorted(declared - expected)) or "none"
        raise _error(
            path,
            qualified,
            f"launch definition must declare exactly {', '.join(sorted(expected))} "
            f"(missing: {missing}; extra: {extra})",
        )
    for name, expected_type in _LAUNCH_ATTRIBUTE_TYPES.items():
        attribute = definition.attributes[name]
        if attribute.type_name != expected_type:
            raise _error(
                path,
                f"{qualified}::{name}",
                f"launch attribute must be typed {expected_type}, "
                f"got {attribute.type_name}",
            )


def _load_launch(
    usage: Any,
    *,
    architecture: Any,
    path: Path,
    qualified: str,
    duplicates: Sequence[str],
) -> LaunchDef:
    if usage.is_variation or usage.variants:
        raise _error(path, qualified, "variation is outside the subset")
    if usage.redefines or usage.subsets or usage.value is not None:
        raise _error(path, qualified, "usage specialization is outside the subset")

    definition = _resolve_part(architecture, usage, path=path, qualified=qualified)
    _check_launch_definition(definition, path=path, qualified=qualified)

    body = usage.body
    if body is None:
        raise _error(path, qualified, "launch usage has no attribute body")
    for kind, members in (
        ("part", body.parts),
        ("connection", body.connections),
        ("binding", body.bindings),
    ):
        for name in members:
            raise _error(
                path,
                f"{qualified}::{name}",
                f"{kind} inside a launch is outside the subset",
            )

    for name in duplicates:
        raise _error(
            path,
            f"{qualified}::{name}",
            "duplicate launch attribute is outside the subset",
        )

    attributes = body.attributes
    expected = set(_LAUNCH_ATTRIBUTE_TYPES)
    for name in attributes:
        if name not in expected:
            raise _error(
                path,
                f"{qualified}::{name}",
                "attribute is outside the launch vocabulary",
            )
    values: dict[str, Any] = {}
    for name, expected_type in _LAUNCH_ATTRIBUTE_TYPES.items():
        attribute = attributes.get(name)
        if attribute is None:
            raise _error(
                path,
                qualified,
                f"missing required launch attribute '{name}'",
            )
        values[name] = _attribute_value(
            attribute,
            expected_type,
            path=path,
            qualified=f"{qualified}::{name}",
        )

    mode = values["mode"]
    readiness = values["readiness"]
    timeout = values["timeout_s"]
    order = values["order"]
    after_process = values["after_process"]
    if mode not in _LAUNCH_MODES:
        raise _error(
            path,
            f"{qualified}::mode",
            f"mode must be one of {', '.join(sorted(_LAUNCH_MODES))}, got {mode!r}",
        )
    if readiness not in _LAUNCH_READINESS:
        raise _error(
            path,
            f"{qualified}::readiness",
            "readiness must be one of "
            f"{', '.join(sorted(_LAUNCH_READINESS))}, got {readiness!r}",
        )
    if not timeout > 0:
        raise _error(
            path,
            f"{qualified}::timeout_s",
            f"launch timeout must be greater than zero, got {timeout!r}",
        )
    if order < 0:
        raise _error(
            path,
            f"{qualified}::order",
            f"launch order must be non-negative, got {order!r}",
        )
    if after_process and not _LAUNCH_IDENTIFIER.fullmatch(after_process):
        raise _error(
            path,
            f"{qualified}::after_process",
            "after_process must be empty or a process/role identifier, "
            f"got {after_process!r}",
        )
    return LaunchDef(
        mode=mode,
        readiness=readiness,
        timeout_s=timeout,
        order=order,
        after_process=after_process,
    )


def _aircraft_key(part_def: Any, *, architecture: Any, path: Path, qualified: str) -> str | None:
    """Stored key of the composition's ``aircraft`` usage, or ``None``."""
    usage = part_def.parts.get("aircraft")
    if usage is None:
        return None
    nested = f"{qualified}::aircraft"
    if usage.is_variation or usage.variants:
        raise _error(path, nested, "variation is outside the subset")
    if usage.redefines or usage.subsets or usage.value is not None:
        raise _error(path, nested, "usage specialization is outside the subset")
    if usage.body is not None:
        raise _error(path, nested, "an aircraft usage body is outside the subset")
    if usage.type_name is None:
        raise _error(path, nested, "part usage has no declared type")
    definition = _resolve_part(architecture, usage, path=path, qualified=nested)
    return architecture.stored_key(definition)


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
    launch_duplicates: Sequence[str] = (),
) -> InstanceDef:
    qualified = f"{package}::{_FEDERATION_DEF}::{usage.name}"
    if usage.type_name is None:
        raise _error(path, qualified, "part usage has no declared type")
    if usage.is_variation or usage.variants:
        raise _error(path, qualified, "variation is outside the subset")
    if usage.redefines or usage.subsets or usage.value is not None:
        raise _error(path, qualified, "usage specialization is outside the subset")

    part_def = _resolve_part(architecture, usage, path=path, qualified=qualified)
    aircraft = _aircraft_key(part_def, architecture=architecture, path=path, qualified=qualified)

    body = usage.body
    if body is None:
        raise _error(path, qualified, "part usage has no attribute body")
    for kind, members in (
        ("connection", body.connections),
        ("binding", body.bindings),
    ):
        for name in members:
            raise _error(
                path,
                f"{qualified}::{name}",
                f"{kind} inside a Federation instance is outside the subset",
            )

    launch: LaunchDef | None = None
    for name in body.parts:
        if name != _LAUNCH:
            raise _error(
                path,
                f"{qualified}::{name}",
                "nested part inside a Federation instance is outside the subset; "
                "only 'part launch : LaunchSpec' is accepted",
            )
    if _LAUNCH in body.parts:
        launch = _load_launch(
            body.parts[_LAUNCH],
            architecture=architecture,
            path=path,
            qualified=f"{qualified}::{_LAUNCH}",
            duplicates=launch_duplicates,
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

    scenario: str | None = None
    for name in _OPTIONAL_STRING_ATTRIBUTES:
        attribute = attributes.get(name)
        if attribute is not None:
            values[name] = _attribute_value(
                attribute,
                "String",
                path=path,
                qualified=f"{qualified}::{name}",
            )
            scenario = str(values[name])

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
        scenario=scenario,
        launch=launch,
        aircraft=aircraft,
    )


def load_federation(
    path: Path | str, *, includes: Sequence[Path | str] = ()
) -> FederationDef:
    """Parse *path* and return the federation setup it declares.

    The supported subset is one primary ``package`` holding ``part def
    Federation``, its composition ``part def``s, and the part definitions the
    instances use; imports and included roots supply qualified vocabulary. See
    ``docs/breakdown/02-architecture/sysml-subset.md``. Anything else raises
    :class:`SysMLError` naming the offender.
    """
    path = Path(path)
    vocabulary = sos_definitions()
    include_paths = [Path(entry) for entry in includes]
    try:
        architecture = pycps_sysml2.load(path, vocabulary, *include_paths)
    except Exception as exc:  # parser errors carry no qualified name
        raise SysMLError(f"cannot parse model: {exc}", path=path) from exc

    package = architecture.package_name
    if not package:
        raise SysMLError("model declares no package", path=path)

    for kind, definitions in (
        ("port def", architecture.port_definitions),
        ("attribute def", architecture.attribute_definitions),
        ("requirement def", architecture.requirement_definitions),
        ("constraint def", architecture.constraint_definitions),
    ):
        for key in definitions:
            if key in architecture.included_definitions:
                continue
            raise _error(
                path,
                key if "::" in key else f"{package}::{key}",
                f"{kind} is outside the supported SysML subset",
            )

    federation = architecture.part_definitions.get(
        _FEDERATION_DEF
    ) or architecture.part_definitions.get(f"{package}::{_FEDERATION_DEF}")
    if federation is None or (
        architecture.stored_key(federation) in architecture.included_definitions
    ):
        raise _error(
            path,
            f"{package}::{_FEDERATION_DEF}",
            f"missing 'part def {_FEDERATION_DEF}'",
        )

    for key, part_def in architecture.part_definitions.items():
        if key in architecture.included_definitions or part_def is federation:
            continue
        _check_entity_definition(
            part_def, architecture=architecture, package=package, path=path
        )

    _check_federation_definition(federation, package=package, path=path)
    if not federation.parts:
        raise _error(
            path,
            f"{package}::{_FEDERATION_DEF}",
            "Federation declares no part instances",
        )

    counts = _multiplicities(path, package)
    duplicates = _launch_duplicates(path)
    instances: list[InstanceDef] = []
    for usage in federation.parts.values():
        instances.append(
            _load_instance(
                usage,
                architecture=architecture,
                package=package,
                path=path,
                counts=counts,
                launch_duplicates=duplicates.get(usage.name, ()),
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
