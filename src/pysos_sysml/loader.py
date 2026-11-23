"""Load the supported SysML subset into :mod:`pysos_sysml.model`.

Parsing is delegated wholesale to ``pycps_sysml2.load``. This module only
walks the repo-owned ``Architecture`` model and rejects everything the subset
does not define. The one exception is part-usage multiplicity: ``pycps_sysml2``
0.2.0 does not retain it on ``PartUsage`` (see
``docs/breakdown/02-architecture/layers.md``), so :func:`_multiplicities`
reads the single-line ``[N]`` annotation lexically. Structure, names, types,
and attribute values still come from the parser.

Nothing unsupported is ignored: every rejected definition, usage, member,
attribute, or value raises :class:`SysMLError` with the offending qualified
name and the source path. The promoted entity plane may also carry local marker
``port def``s, ``ParameterSet`` bodies, and specialization/attributes/ports/
bindings on composition defs; those are accepted as model structure and are not
lowered.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Mapping, Sequence
from importlib import resources
from pathlib import Path
from types import MappingProxyType
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
_REQUIRED_INSTANCE_ATTRIBUTES = (
    "site",
    "application",
    "entity",
    "telemetryPort",
    "marking",
    "command",
    "cwd",
)
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


def _check_port_usage(
    usage: Any, *, architecture: Any, path: Path, qualified: str
) -> None:
    """A port usage must name a port definition the model can see."""
    if usage.type_name is None:
        raise _error(path, qualified, "port usage has no declared type")
    try:
        definition = architecture.resolve_port(usage)
    except ValueError as exc:
        raise _error(path, qualified, str(exc)) from exc
    if definition is None:
        raise _error(
            path,
            qualified,
            f"unknown port definition '{usage.type_name}'",
        )


def _is_parameter_set_definition(architecture: Any, definition: Any) -> bool:
    """Whether *definition* specializes the imported ``ParameterSet``.

    The set itself is vocabulary, not a local definition: a primary
    ``attribute def`` is accepted only when its specialization chain reaches
    ``ParameterSet``.
    """
    if not definition.specializes:
        return False
    seen: set[str] = set()
    stack = [definition]
    while stack:
        current = stack.pop()
        key = architecture.stored_key(current)
        if key in seen:
            continue
        seen.add(key)
        if current is not definition and current.name == "ParameterSet":
            return True
        for supertype in current.specializes:
            try:
                base = architecture.resolve_attribute_def(supertype)
            except ValueError:
                base = None
            if base is not None:
                stack.append(base)
    return False


def _check_entity_definition(
    part_def: Any, *, architecture: Any, package: str, path: Path
) -> None:
    """A primary non-Federation composition.

    Specialization, attributes, ports, bindings and nested part usages are
    accepted; each specialization and port type must resolve. Variations,
    connections, constraints, and usage specialization stay outside the
    subset. A nested part's body is carried but not interpreted here: the
    participant resolver validates the ``launch`` body when it is used.
    """
    qualified = f"{package}::{part_def.name}"
    if part_def.is_variation or part_def.variants:
        raise _error(path, qualified, "variation is outside the subset")
    for kind, members in (
        ("connection", part_def.connections),
        ("constraint", part_def.constraints),
    ):
        for name in members:
            raise _error(
                path,
                f"{qualified}::{name}",
                f"{kind} is outside the supported SysML subset",
            )
    for supertype in part_def.specializes:
        nested = f"{qualified}:> {supertype}"
        try:
            base = architecture.resolve_part(supertype)
        except ValueError as exc:
            raise _error(path, nested, str(exc)) from exc
        if base is None:
            raise _error(path, nested, f"unknown part definition '{supertype}'")
    for name, usage in part_def.ports.items():
        _check_port_usage(
            usage,
            architecture=architecture,
            path=path,
            qualified=f"{qualified}::{name}",
        )
    for name, usage in part_def.parts.items():
        nested = f"{qualified}::{name}"
        if usage.is_variation or usage.variants:
            raise _error(path, nested, "variation is outside the subset")
        if usage.redefines or usage.subsets or usage.value is not None:
            raise _error(path, nested, "usage specialization is outside the subset")
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


def _base_aircraft_key(
    definition: Any, *, architecture: Any, path: Path, qualified: str
) -> str:
    """Stored key of the imported model *definition* specializes.

    A direct included definition is its own answer (the legacy
    ``part aircraft : AircraftModel`` shape). A primary variant such as
    ``RedInterceptor :> AircraftVariant :> AircraftModel`` walks its
    specialization chain to the first included ancestor and returns that
    stored key (for example ``Aircraft::AircraftModel``).
    """
    direct = architecture.stored_key(definition)
    if direct in architecture.included_definitions:
        return direct
    seen: set[str] = set()
    stack = [definition]
    while stack:
        current = stack.pop()
        key = architecture.stored_key(current)
        if key in seen:
            continue
        seen.add(key)
        if key in architecture.included_definitions:
            return key
        for supertype in current.specializes:
            try:
                base = architecture.resolve_part(supertype)
            except ValueError as exc:
                raise _error(path, qualified, str(exc)) from exc
            if base is None:
                raise _error(
                    path,
                    qualified,
                    f"unknown part definition '{supertype}'",
                )
            stack.append(base)
    return direct


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
    return _base_aircraft_key(
        definition, architecture=architecture, path=path, qualified=nested
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


def _definition_attribute_value(
    attribute: Any, expected: str, *, path: Path, qualified: str
) -> Any:
    """Value of a definition-level attribute, already parsed to a native literal.

    Definition attributes come through ``sysmlpy``'s value normalization, so a
    quoted String is already a ``str`` without quotes. Usage-body attributes
    (the launch body) keep authored text and still go through
    :func:`_attribute_value`.
    """
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
    if isinstance(attribute.value, str):
        return attribute.value
    raise _error(
        path,
        qualified,
        f"expected a String literal, got {attribute.value!r}",
    )


def _member_attribute(
    attributes: Any,
    name: str,
    expected: str,
    *,
    path: Path,
    qualified: str,
    required: bool = True,
) -> Any:
    attribute = attributes.get(name)
    if attribute is None:
        if required:
            raise _error(path, qualified, f"missing required attribute '{name}'")
        return None
    return _definition_attribute_value(
        attribute,
        expected,
        path=path,
        qualified=f"{qualified}::{name}",
    )


def _set_definition(
    architecture: Any,
    attributes: Any,
    usage_name: str,
    *,
    path: Path,
    qualified: str,
    required: bool = True,
) -> Any:
    """The attribute definition a variant's ``identity``/``transport``/... names."""
    attribute = attributes.get(usage_name)
    if attribute is None:
        if required:
            raise _error(path, qualified, f"missing required attribute '{usage_name}'")
        return None
    nested = f"{qualified}::{usage_name}"
    try:
        definition = architecture.resolve_attribute_def(attribute)
    except ValueError as exc:
        raise _error(path, nested, str(exc)) from exc
    if definition is None:
        raise _error(
            path,
            nested,
            f"unknown attribute definition '{attribute.type_name}'",
        )
    return definition


def _set_members(architecture: Any, definition: Any) -> Any:
    return pycps_sysml2.effective_members(architecture, definition).attributes


def _member_values(attributes: Any) -> Mapping[str, Any]:
    """Read-only name-to-value view of effective attribute members.

    Members without a literal value (an inherited declaration the model never
    set) are omitted, so every exposed value is an int/float/str/tuple the
    model actually stores.
    """
    return MappingProxyType(
        {
            name: attribute.value
            for name, attribute in attributes.items()
            if attribute.value is not None
        }
    )


def _bind_endpoint(value: str, *, path: Path, qualified: str) -> tuple[str, int]:
    """Split an authored ``host:port`` transport address."""
    host, separator, port_text = value.rpartition(":")
    if not separator or not host:
        raise _error(
            path,
            qualified,
            f"bind_address must be 'host:port', got {value!r}",
        )
    port = _integer_literal(port_text, path=path, qualified=qualified)
    if not 1 <= port <= 65535:
        raise _error(
            path,
            qualified,
            f"bind_address port must be between 1 and 65535, got {port!r}",
        )
    return host, port


def _count_for_usage(
    usage: Any, counts: dict[str, tuple[str, int]], *, path: Path, qualified: str
) -> int:
    annotation = counts.get(usage.name)
    if annotation is None:
        return 1
    annotated_type, count = annotation
    if annotated_type != usage.type_name:
        raise _error(
            path,
            qualified,
            f"multiplicity annotation names type '{annotated_type}' "
            f"but the parser resolved '{usage.type_name}'",
        )
    return count


def _load_participant_instance(
    usage: Any,
    part_def: Any,
    *,
    architecture: Any,
    package: str,
    path: Path,
    counts: dict[str, tuple[str, int]],
) -> InstanceDef:
    """Resolve a bare ``part <name> : <ParticipantDef>;`` usage.

    The participant owns ``aircraft`` (the variant) and ``application`` (the
    runnable wrapper); the variant owns the ``scenario``, ``identity`` and
    ``transport`` parameter sets. Everything is read through
    ``effective_members`` so inherited members are merged by the parser layer.
    """
    qualified = f"{package}::{_FEDERATION_DEF}::{usage.name}"
    members = pycps_sysml2.effective_members(architecture, part_def)

    aircraft_usage = members.parts.get("aircraft")
    if aircraft_usage is None:
        raise _error(path, qualified, "missing required nested part 'aircraft'")
    nested = f"{qualified}::aircraft"
    variant = _resolve_part(
        architecture, aircraft_usage, path=path, qualified=nested
    )
    aircraft = _base_aircraft_key(
        variant, architecture=architecture, path=path, qualified=nested
    )
    variant_members = pycps_sysml2.effective_members(architecture, variant)

    identity = _set_definition(
        architecture,
        variant_members.attributes,
        "identity",
        path=path,
        qualified=qualified,
    )
    identity_members = _set_members(architecture, identity)
    identity_values = _member_values(identity_members)
    site = int(
        _member_attribute(
            identity_members,
            "entity_site",
            "Integer",
            path=path,
            qualified=f"{qualified}::identity",
        )
    )
    application = int(
        _member_attribute(
            identity_members,
            "entity_application",
            "Integer",
            path=path,
            qualified=f"{qualified}::identity",
        )
    )
    entity = int(
        _member_attribute(
            identity_members,
            "entity_entity",
            "Integer",
            path=path,
            qualified=f"{qualified}::identity",
        )
    )
    marking = str(
        _member_attribute(
            identity_members,
            "marking_characters",
            "String",
            path=path,
            qualified=f"{qualified}::identity",
        )
    )

    transport = _set_definition(
        architecture,
        variant_members.attributes,
        "transport",
        path=path,
        qualified=qualified,
    )
    transport_members = _set_members(architecture, transport)
    transport_values = _member_values(transport_members)
    protocol = str(
        _member_attribute(
            transport_members,
            "transport",
            "String",
            path=path,
            qualified=f"{qualified}::transport",
        )
    )
    if protocol != "udp":
        raise _error(
            path,
            f"{qualified}::transport",
            f"transport must be 'udp', got {protocol!r}",
        )
    bind_address = str(
        _member_attribute(
            transport_members,
            "bind_address",
            "String",
            path=path,
            qualified=f"{qualified}::transport",
        )
    )
    host, telemetry = _bind_endpoint(
        bind_address, path=path, qualified=f"{qualified}::transport"
    )

    scenario = _set_definition(
        architecture,
        variant_members.attributes,
        "scenario",
        path=path,
        qualified=qualified,
        required=False,
    )
    scenario_values: dict[str, Any] = {}
    if scenario is not None:
        scenario_values = {
            name: attribute.value
            for name, attribute in _set_members(architecture, scenario).items()
        }

    experiment = _set_definition(
        architecture,
        variant_members.attributes,
        "experiment",
        path=path,
        qualified=qualified,
        required=False,
    )
    experiment_values = (
        _member_values(_set_members(architecture, experiment))
        if experiment is not None
        else _member_values({})
    )

    application_usage = members.parts.get("application")
    if application_usage is None:
        raise _error(path, qualified, "missing required nested part 'application'")
    nested = f"{qualified}::application"
    application_def = _resolve_part(
        architecture, application_usage, path=path, qualified=nested
    )
    app_members = pycps_sysml2.effective_members(architecture, application_def)
    application_values = _member_values(app_members.attributes)
    waypoint_frame = application_values.get("waypointFrame")
    if waypoint_frame is not None:
        waypoint_frame = str(waypoint_frame)
    # The scenario *name* is application metadata, not a variant parameter set
    # value; lowering it here is what makes `lower._env` emit PYSOS_SCENARIO.
    application_scenario = application_values.get("scenario")
    if application_scenario is not None:
        application_scenario = str(application_scenario)
    command = str(
        _member_attribute(
            app_members.attributes,
            "command",
            "String",
            path=path,
            qualified=nested,
        )
    )
    cwd = str(
        _member_attribute(
            app_members.attributes,
            "cwd",
            "String",
            path=path,
            qualified=nested,
        )
    )
    _member_attribute(
        app_members.attributes,
        "roles",
        "String",
        path=path,
        qualified=nested,
        required=False,
    )
    launch: LaunchDef | None = None
    launch_usage = app_members.parts.get("launch")
    if launch_usage is not None:
        launch = _load_launch(
            launch_usage,
            architecture=architecture,
            path=path,
            qualified=f"{nested}::{_LAUNCH}",
            duplicates=(),
        )

    count = _count_for_usage(usage, counts, path=path, qualified=qualified)
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
            EndpointDef(name="telemetry", port=telemetry + index, host=host)
            for index in range(count)
        ],
        control_ports=[],
        command=command,
        cwd=cwd,
        launch=launch,
        aircraft=aircraft,
        scenario=application_scenario,
        scenario_values=MappingProxyType(scenario_values),
        identity_values=identity_values,
        transport_values=transport_values,
        application_values=application_values,
        experiment_values=experiment_values,
        waypoint_frame=waypoint_frame,
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
    body = usage.body
    if body is None:
        return _load_participant_instance(
            usage,
            part_def,
            architecture=architecture,
            package=package,
            path=path,
            counts=counts,
        )
    aircraft = _aircraft_key(part_def, architecture=architecture, path=path, qualified=qualified)

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
    for name in _REQUIRED_INSTANCE_ATTRIBUTES:
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

    control: int | None = None
    control_attribute = attributes.get("controlPort")
    if control_attribute is not None:
        control = int(
            _attribute_value(
                control_attribute,
                "Integer",
                path=path,
                qualified=f"{qualified}::controlPort",
            )
        )

    count = _count_for_usage(usage, counts, path=path, qualified=qualified)

    site = int(values["site"])
    application = int(values["application"])
    entity = int(values["entity"])
    marking = str(values["marking"])
    telemetry = int(values["telemetryPort"])

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
        control_ports=(
            []
            if control is None
            else [
                EndpointDef(name="control", port=control + index)
                for index in range(count)
            ]
        ),
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
    instances use; imports and included roots supply qualified vocabulary. A
    Federation usage may carry the schema-1 body, or be bare and name a
    participant def whose ``aircraft``/``application`` wrappers resolve the
    entity facts. See ``docs/breakdown/02-architecture/sysml-subset.md``.
    Anything else raises :class:`SysMLError` naming the offender.
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

    for key, port_def in architecture.port_definitions.items():
        if key in architecture.included_definitions:
            continue
        if port_def.attributes:
            raise _error(
                path,
                key if "::" in key else f"{package}::{key}",
                "port def is outside the supported SysML subset unless it is "
                "a marker with no attributes",
            )
    for key, attribute_def in architecture.attribute_definitions.items():
        if key in architecture.included_definitions:
            continue
        if not _is_parameter_set_definition(architecture, attribute_def):
            raise _error(
                path,
                key if "::" in key else f"{package}::{key}",
                "attribute def is outside the supported SysML subset unless "
                "it specializes ParameterSet",
            )
    for kind, definitions in (
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
