"""Lower the setup IR to the ``pysos_coordinate`` execution manifest.

The manifest is schema **version 1**, owned by ``pysos_coordinate`` and defined
in its ``docs/breakdown/02-architecture/manifest.md``. This module does not
import that package and does not execute anything: it produces a plain
dictionary that conforms to the owned schema. Occurrence expansion happens
here, so one authored instance with multiplicity ``N`` becomes ``name_1`` …
``name_N`` (a scalar instance keeps its bare name).
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef

__all__ = ["dump_manifest", "manifest_json", "to_manifest"]

SCHEMA_VERSION = 1
TIMING_POLICY = "wall_clock"
DEFAULT_STARTUP_TIMEOUT = 30.0


def _entity(entity: EntityDef) -> dict[str, Any]:
    # pysos_coordinate requires text ids even though the SysML attributes are
    # Integer: the manifest is the boundary where the identifier becomes text.
    return {
        "site": str(entity.site),
        "application": str(entity.application),
        "entity": str(entity.entity),
        "marking": entity.marking,
    }


def _endpoint(endpoint: EndpointDef) -> dict[str, Any]:
    # Endpoint.name is setup vocabulary (telemetry/control channel); the
    # manifest endpoint is only a host/port pair.
    return {
        "port": endpoint.port,
        "host": endpoint.host,
    }


def _argv(instance: InstanceDef) -> list[str]:
    try:
        argv = shlex.split(instance.command)
    except ValueError as exc:
        raise ValueError(
            f"instance '{instance.name}': command is not a valid argv string: {exc}"
        ) from None
    if not argv:
        raise ValueError(f"instance '{instance.name}': command must not be empty")
    return argv


def _check_alignment(instance: InstanceDef) -> None:
    for field_name in ("entities", "telemetry_ports", "control_ports"):
        actual = len(getattr(instance, field_name))
        if actual != instance.count:
            raise ValueError(
                f"instance '{instance.name}' declares count {instance.count} "
                f"but has {actual} {field_name}"
            )


def _occurrence_name(instance: InstanceDef, index: int) -> str:
    if instance.count == 1:
        return instance.name
    return f"{instance.name}_{index + 1}"


def to_manifest(federation: FederationDef) -> dict[str, Any]:
    """Return the schema-1 manifest dictionary for *federation*.

    The result is plain JSON-ready data with the keys required by
    ``pysos_coordinate``: top-level ``schema``, ``name``, ``timing`` and
    ``instances``; each instance carries ``name``, ``command`` (argv),
    ``cwd``, ``env``, ``entities``, ``telemetry``, ``control`` and
    ``startup_timeout``. ``env`` is reserved and empty in 0.1.0; the subset has
    no environment attributes.
    """
    instances: list[dict[str, Any]] = []
    for instance in federation.instances:
        _check_alignment(instance)
        argv = _argv(instance)
        for index in range(instance.count):
            instances.append(
                {
                    "name": _occurrence_name(instance, index),
                    "command": list(argv),
                    "cwd": instance.cwd,
                    "env": {},
                    "entities": [_entity(instance.entities[index])],
                    "telemetry": [_endpoint(instance.telemetry_ports[index])],
                    "control": [_endpoint(instance.control_ports[index])],
                    "startup_timeout": DEFAULT_STARTUP_TIMEOUT,
                }
            )
    return {
        "schema": SCHEMA_VERSION,
        "name": federation.name,
        "timing": TIMING_POLICY,
        "instances": instances,
    }


def manifest_json(federation: FederationDef) -> str:
    """Deterministic JSON text: sorted keys, two-space indent, newline."""
    return json.dumps(to_manifest(federation), sort_keys=True, indent=2) + "\n"


def dump_manifest(federation: FederationDef, path: Path | str) -> None:
    """Write :func:`manifest_json` to *path* as UTF-8."""
    Path(path).write_text(manifest_json(federation), encoding="utf-8")
