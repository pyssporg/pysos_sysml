"""Self-contained system-of-systems setup IR.

These dataclasses are the contract between :mod:`pysos_sysml.loader` and
:mod:`pysos_sysml.lower` and nothing else. They deliberately do not import
``pysos_coordinate`` (or any other execution package): the manifest dictionary
crosses that boundary, not a shared type.

A federation is authored once in SysML and may contain several instances of
one part definition. ``InstanceDef.count`` keeps the authored multiplicity and
the per-occurrence lists stay aligned with it: ``entities[i]``,
``telemetry_ports[i]`` and ``control_ports[i]`` all belong to occurrence
``name_<i+1>`` when ``count > 1``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "EndpointDef",
    "EntityDef",
    "FederationDef",
    "InstanceDef",
]


@dataclass
class EndpointDef:
    """One telemetry or control endpoint of an instance occurrence."""

    name: str
    port: int
    host: str = "127.0.0.1"


@dataclass
class EntityDef:
    """The simulation identity an instance occurrence joins."""

    site: int
    application: int
    entity: int
    marking: str


@dataclass
class InstanceDef:
    """One authored ``part`` usage on ``Federation``.

    ``count`` is the declared multiplicity (1 when omitted). The three lists
    each hold ``count`` entries in occurrence order. ``part_def`` is the bare
    name of the part definition the usage is typed by. ``scenario`` is the
    optional authored flight scenario; one value applies to every occurrence
    and ``None`` means no scenario was authored.
    """

    name: str
    part_def: str
    count: int
    entities: list[EntityDef]
    telemetry_ports: list[EndpointDef]
    control_ports: list[EndpointDef]
    command: str
    cwd: str
    scenario: str | None = None


@dataclass
class FederationDef:
    """A complete setup: named instances plus loader metadata.

    ``metadata`` is a plain string map (package, definition, source file). It
    is provenance for humans; it is not part of the execution manifest.
    """

    name: str
    instances: list[InstanceDef]
    metadata: dict[str, Any] = field(default_factory=dict)
