---
id: INFO-004
type: info
title: Execution Manifest, Schemas 1 And 2
summary: How pysos_sysml lowers its IR to the schema-1 and schema-2 manifest owned by pysos_coordinate, including Unix domain socket endpoints, launch timeout and producer env, and how determinism and the round trip are protected.
date: 2026-11-24
status: current
---

# Execution Manifest, Schemas 1 And 2

The manifest schema is **owned by `pysos_coordinate`**, not by this package. Its
normative definition is
[`pysos_coordinate/docs/breakdown/02-architecture/manifest.md`](https://github.com/pyssporg/pysos_coordinate/blob/main/docs/breakdown/02-architecture/manifest.md).
`pysos_sysml.lower` targets schemas 1 and 2 and documents its mapping here; it
does not import the owner and does not execute the result. Schema 1 is
UDP-only; a setup with a Unix domain socket endpoint lowers as schema 2.

## Emitted shape

```json
{
  "schema": 1,
  "name": "TwoInstances",
  "timing": "wall_clock",
  "instances": [
    {
      "name": "alpha",
      "command": ["alpha-engine", "--mode", "fast"],
      "cwd": "/opt/alpha",
      "env": {
        "PYSOS_TELEMETRY_PORT": "5551",
        "PYSOS_CONTROL_PORT": "5651",
        "PYSOS_SCENARIO": "cruise",
        "PYSOS_LAUNCH_MODE": "supervised",
        "PYSOS_READINESS": "port_bound"
      },
      "entities": [
        {"site": "1", "application": "10", "entity": "1", "marking": "UNCLASSIFIED"}
      ],
      "telemetry": [{"host": "127.0.0.1", "port": 5551}],
      "control": [{"host": "127.0.0.1", "port": 5651}],
      "startup_timeout": 12.5
    }
  ]
}
```

The top level carries exactly `schema`, `name`, `timing`, and `instances`. Every
instance carries exactly `name`, `command`, `cwd`, `env`, `entities`,
`telemetry`, and `startup_timeout`, plus `control` when the setup authors a
`controlPort`.

`schema` is `1` for a UDP-only setup, so its manifest is byte-identical to a
pre-Unix lowering. It is `2` when any endpoint is a Unix domain socket. A Unix
endpoint keeps the same `telemetry` / `control` slots but changes their shape
and the corresponding env keys:

```json
{
  "schema": 2,
  "instances": [
    {
      "env": {
        "PYSOS_TRANSPORT": "unix",
        "PYSOS_TELEMETRY_PATH": "@red-telemetry",
        "PYSOS_CONTROL_PATH": "@red-control"
      },
      "telemetry": [{"transport": "unix", "path": "@red-telemetry"}],
      "control": [{"transport": "unix", "path": "@red-control"}]
    }
  ]
}
```

The omitted instance fields follow the UDP example; the snippet is illustrative,
not a complete manifest.

## Mapping

| Manifest field | Source and conversion |
| --- | --- |
| `schema` | `1` (`SCHEMA_VERSION`) for UDP-only, `2` (`UNIX_SCHEMA_VERSION`) when any endpoint is a Unix socket |
| `name` | package name (`FederationDef.name`) |
| `timing` | constant `"wall_clock"` (`pysos_sysml.lower.TIMING_POLICY`) |
| `instances[].name` | instance name, or `<name>_<i>` when multiplicity > 1 |
| `instances[].command` | `command` String tokenized to argv with `shlex.split`; no shell runs |
| `instances[].cwd` | `cwd` String |
| `instances[].env` | producer-owned channel: the occurrence telemetry address (`PYSOS_TELEMETRY_PORT`, or `PYSOS_TRANSPORT` + `PYSOS_TELEMETRY_PATH`) and control address (`PYSOS_CONTROL_PORT`, or `PYSOS_CONTROL_PATH`), plus `PYSOS_SCENARIO` when authored plus `PYSOS_LAUNCH_MODE`, `PYSOS_READINESS`, `PYSOS_LAUNCH_ORDER` and `PYSOS_AFTER_PROCESS` when a launch is authored |
| `instances[].entities` | one `EntityDef`: `site`, `application`, `entity` as decimal text, plus `marking` |
| `instances[].telemetry` | one `EndpointDef`: UDP `host`, `port` only, or Unix `{"transport": "unix", "path"}` |
| `instances[].control` | one `EndpointDef`: UDP `host`, `port` only, or Unix `{"transport": "unix", "path"}` |
| `instances[].startup_timeout` | authored `launch.timeout_s` when present, else the reserved default `30.0` |

The SysML attributes `site`, `application`, and `entity` are `Integer`, but the
manifest's `EntityRef` identity is text, so lowering emits their decimal spelling.
`command` is authored as one String and becomes an argv list before it crosses
the boundary; quoting is handled by `shlex.split`, and shell operators are
literal tokens because no shell is involved. The IR keeps `EndpointDef.name`
(the telemetry/control channel), but the manifest endpoint has no name field.

One manifest instance is one process occurrence. Its entity id and, for UDP,
both ports are the occurrence's arithmetic values from
`02-architecture/sysml-subset.md`, so a three-occurrence instance produces
three entries, each with one entity and one endpoint per channel. A Unix bind
address is one socket per process, so the authoring subset limits a Unix
participant to one occurrence. The IR keeps
the resolved aircraft definition (for example `Aircraft::AircraftModel`) and
the launch, but neither adds a manifest key beyond the env values above.

## Environment contract

`env` is the producer-owned channel from the authored setup to the launched
producer process. Lowering always emits exactly these string-to-string keys per
occurrence:

| Key | Value | Present |
| --- | --- | --- |
| `PYSOS_TELEMETRY_PORT` | occurrence UDP telemetry port, decimal text | UDP telemetry only |
| `PYSOS_TRANSPORT` | `unix`, verbatim | Unix telemetry only |
| `PYSOS_TELEMETRY_PATH` | Unix telemetry path/`@name`, verbatim | Unix telemetry only |
| `PYSOS_CONTROL_PORT` | occurrence UDP control port, decimal text | UDP control endpoint only |
| `PYSOS_CONTROL_PATH` | Unix control path/`@name`, verbatim | Unix control endpoint only |
| `PYSOS_SCENARIO` | authored `scenario` value, verbatim | only when authored |
| `PYSOS_LAUNCH_MODE` | authored `launch.mode` value, verbatim | only when a launch is authored |
| `PYSOS_READINESS` | authored `launch.readiness` value, verbatim | only when a launch is authored |
| `PYSOS_LAUNCH_ORDER` | authored `launch.order`, decimal text | only when a launch is authored |
| `PYSOS_AFTER_PROCESS` | authored `launch.after_process` value, verbatim | only when a launch is authored |

A UDP endpoint emits `PYSOS_TELEMETRY_PORT` / `PYSOS_CONTROL_PORT`; a Unix
endpoint emits `PYSOS_TRANSPORT` + `PYSOS_TELEMETRY_PATH` / `PYSOS_CONTROL_PATH`
instead. A UDP-only instance emits the same keys and values as before schema 2,
so existing manifests are unchanged. `PYSOS_READINESS` carries the authored
value verbatim; its accepted vocabulary (`none`, `port_bound`, `socket_bound`,
`log_line`) is defined in
[`sysml-subset.md`](sysml-subset.md), not here.

The scenario and launch are authored once per part usage, so every occurrence
of that usage carries the same values; the port/path keys differ per occurrence.
`env` has no other keys. `pysos_coordinate` passes `env` through opaquely: it
layers the mapping over `os.environ` and validates only that keys and values are
strings, so these key names are this package's contract with the producer, not
the schema owner's.

## Determinism

`manifest_json` uses `json.dumps(..., sort_keys=True, indent=2)` plus one
trailing newline. `dump_manifest` writes that exact UTF-8 text. Repeated runs on
the same input are byte-identical, so a manifest can be compared, committed, or
hashed without normalisation.

`tests/fixtures/two_instances.manifest.json` is the checked-in lowering of
`two_instances.sysml`. The round-trip test compares the current lowering with
that file and, when the optional `[dev]` dependency `pysos-coordinate` is
installed, parses it through the owner's public API and CLI in
validation/port mode. Without the owner the test skips; lowering itself never
imports it.

## Drift check

`pysos_sysml.manifest.render(path)` returns
`manifest_json(load_federation(path))`, so it inherits the same formatting
rules and never re-implements them. `check(path, expected_path)` compares those
UTF-8 bytes with the file and returns `False` when the file is stale or
missing.

`pysos-sysml manifest FILE -o PATH --check` is the CI form. It requires `-o`,
never writes the file, prints `ok: PATH is up to date` and exits 0 on an exact
match, and treats drift as exit 1 with a short stderr message plus a unified
diff bounded to 20 lines. A missing file is drift too: exit 1 and a short
stderr message, with no diff. Usage errors and `SysMLError` keep exit 2.
