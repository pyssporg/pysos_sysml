"""Lower the setup IR to the ``pysos_coordinate`` execution manifest.

The manifest is schema **version 1**, or **version 2** when an endpoint is a
Unix domain socket, owned by ``pysos_coordinate`` and defined in its
``docs/breakdown/02-architecture/manifest.md``. This module does not import that
package and does not execute anything: it produces a plain dictionary that
conforms to the owned schema. Occurrence expansion happens
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
UNIX_SCHEMA_VERSION = 2
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
    # Endpoint.name is setup vocabulary (telemetry/control channel). A UDP
    # endpoint is only a host/port pair; a Unix endpoint is the schema-2
    # transport/path shape and must not repeat host or port.
    if endpoint.transport == "unix":
        return {
            "transport": "unix",
            "path": endpoint.path,
        }
    return {
        "port": endpoint.port,
        "host": endpoint.host,
    }


def _schema(federation: FederationDef) -> int:
    """Schema 2 when any endpoint is a Unix domain socket, else schema 1."""
    for instance in federation.instances:
        for endpoint in (*instance.telemetry_ports, *instance.control_ports):
            if endpoint.transport == "unix":
                return UNIX_SCHEMA_VERSION
    return SCHEMA_VERSION


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
    for field_name in ("entities", "telemetry_ports"):
        actual = len(getattr(instance, field_name))
        if actual != instance.count:
            raise ValueError(
                f"instance '{instance.name}' declares count {instance.count} "
                f"but has {actual} {field_name}"
            )
    # A setup either has a control channel for every occurrence or none at all.
    controls = len(instance.control_ports)
    if controls not in (0, instance.count):
        raise ValueError(
            f"instance '{instance.name}' declares count {instance.count} "
            f"but has {controls} control_ports"
        )


def _occurrence_name(instance: InstanceDef, index: int) -> str:
    if instance.count == 1:
        return instance.name
    return f"{instance.name}_{index + 1}"


def _env(instance: InstanceDef, index: int) -> dict[str, str]:
    """Producer-owned environment channel for occurrence *index*.

    ``pysos_coordinate`` passes ``env`` through opaquely: it layers the mapping
    over the supervisor's environment and validates only that it is
    string-to-string. The setup layer therefore owns these key names and emits
    decimal spellings for the ports; the launched producer reads its scenario
    and endpoints from its own environment.
    """
    env: dict[str, str] = {}
    telemetry = instance.telemetry_ports[index]
    if telemetry.transport == "unix":
        env["PYSOS_TRANSPORT"] = "unix"
        env["PYSOS_TELEMETRY_PATH"] = str(telemetry.path)
    else:
        env["PYSOS_TELEMETRY_PORT"] = str(telemetry.port)
    if instance.control_ports:
        control = instance.control_ports[index]
        if control.transport == "unix":
            env["PYSOS_CONTROL_PATH"] = str(control.path)
        else:
            env["PYSOS_CONTROL_PORT"] = str(control.port)
    if instance.scenario is not None:
        env["PYSOS_SCENARIO"] = instance.scenario
    if instance.launch is not None:
        env["PYSOS_LAUNCH_MODE"] = instance.launch.mode
        env["PYSOS_READINESS"] = instance.launch.readiness
        env["PYSOS_LAUNCH_ORDER"] = str(instance.launch.order)
        env["PYSOS_AFTER_PROCESS"] = instance.launch.after_process
    return env


def to_manifest(federation: FederationDef) -> dict[str, Any]:
    """Return the schema-1 manifest dictionary for *federation*.

    The result is plain JSON-ready data with the keys required by
    ``pysos_coordinate``: top-level ``schema``, ``name``, ``timing`` and
    ``instances``; each instance carries ``name``, ``command`` (argv),
    ``cwd``, ``env``, ``entities``, ``telemetry`` and ``startup_timeout``.
    ``control`` is emitted only when the instance declares a control endpoint.
    ``env`` is the producer-owned channel and always carries the telemetry
    address: ``PYSOS_TELEMETRY_PORT`` for UDP or ``PYSOS_TRANSPORT`` plus
    ``PYSOS_TELEMETRY_PATH`` for a Unix socket. It carries the control address
    when a control endpoint exists (``PYSOS_CONTROL_PORT`` or
    ``PYSOS_CONTROL_PATH``) and ``PYSOS_SCENARIO`` when the instance authors a
    scenario string. A promoted variant keeps its scenario in its SSP, so it
    exposes ``scenario_values`` without lowering them. The top-level ``schema``
    is 2 when any endpoint is a Unix socket, otherwise 1.
    ``PYSOS_LAUNCH_MODE`` / ``PYSOS_READINESS`` / ``PYSOS_LAUNCH_ORDER`` /
    ``PYSOS_AFTER_PROCESS`` are emitted when the instance authors a launch.
    ``startup_timeout`` is the launch ``timeout_s`` when present, else the
    reserved default.
    """
    instances: list[dict[str, Any]] = []
    for instance in federation.instances:
        _check_alignment(instance)
        argv = _argv(instance)
        for index in range(instance.count):
            entry = {
                "name": _occurrence_name(instance, index),
                "command": list(argv),
                "cwd": instance.cwd,
                "env": _env(instance, index),
                "entities": [_entity(instance.entities[index])],
                "telemetry": [_endpoint(instance.telemetry_ports[index])],
                "startup_timeout": (
                    instance.launch.timeout_s
                    if instance.launch is not None
                    else DEFAULT_STARTUP_TIMEOUT
                ),
            }
            if instance.control_ports:
                entry["control"] = [_endpoint(instance.control_ports[index])]
            instances.append(entry)
    return {
        "schema": _schema(federation),
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
