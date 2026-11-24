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

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "EndpointDef",
    "EntityDef",
    "FederationDef",
    "InstanceDef",
    "LaunchDef",
]


@dataclass
class EndpointDef:
    """One telemetry or control endpoint of an instance occurrence.

    A UDP endpoint is the default and uses ``host`` and ``port``. A Unix domain
    socket endpoint sets ``transport="unix"`` and ``path`` (an absolute path or
    an abstract ``@name``) and leaves ``port`` as ``None``. The first three
    fields keep their historical order so ``EndpointDef(name, port, host)``
    keeps working.
    """

    name: str
    port: int | None
    host: str = "127.0.0.1"
    transport: str = "udp"
    path: str | None = None

    @classmethod
    def unix(cls, path: str, name: str = "telemetry") -> EndpointDef:
        """A Unix domain socket endpoint at an absolute path or ``@name``."""
        return cls(name=name, port=None, transport="unix", path=path)


@dataclass
class EntityDef:
    """The simulation identity an instance occurrence joins."""

    site: int
    application: int
    entity: int
    marking: str


@dataclass
class LaunchDef:
    """The optional ``part launch : LaunchSpec`` of one authored instance.

    ``mode``, ``readiness``, ``order`` and ``after_process`` are validated
    vocabulary values; the loader normalizes ``timeout_s`` to a float. Lowering
    turns the timeout into ``startup_timeout`` and the launch facts into
    producer environment keys.
    """

    mode: str
    readiness: str
    timeout_s: float
    order: int
    after_process: str


@dataclass
class InstanceDef:
    """One authored ``part`` usage on ``Federation``.

    ``count`` is the declared multiplicity (1 when omitted). The three lists
    each hold ``count`` entries in occurrence order; ``control_ports`` may be
    empty when the setup has no control channel. ``part_def`` is the bare name
    of the part definition the usage is typed by. ``scenario`` is the optional
    authored flight scenario string from the schema-1 body; one value applies
    to every occurrence and ``None`` means no scenario was authored.
    ``scenario_values``, ``identity_values``, ``transport_values``,
    ``application_values`` and ``experiment_values`` expose a promoted
    variant's/application's effective members as read-only name-to-value
    mappings; none of them is lowered. ``waypoint_frame`` is the application's
    ``waypointFrame`` value when present. ``launch`` is the optional launch
    vocabulary; ``aircraft`` is the resolved stored key of the model the
    variant specializes (for example ``Aircraft::AircraftModel``), or ``None``
    when the entity declares none.
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
    launch: LaunchDef | None = None
    aircraft: str | None = None
    scenario_values: Mapping[str, Any] = field(default_factory=dict)
    identity_values: Mapping[str, Any] = field(default_factory=dict)
    transport_values: Mapping[str, Any] = field(default_factory=dict)
    application_values: Mapping[str, Any] = field(default_factory=dict)
    experiment_values: Mapping[str, Any] = field(default_factory=dict)
    waypoint_frame: str | None = None


@dataclass
class FederationDef:
    """A complete setup: named instances plus loader metadata.

    ``metadata`` is a plain string map (package, definition, source file). It
    is provenance for humans; it is not part of the execution manifest.
    """

    name: str
    instances: list[InstanceDef]
    metadata: dict[str, Any] = field(default_factory=dict)
