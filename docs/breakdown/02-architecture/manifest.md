---
id: INFO-004
type: info
title: Execution Manifest, Schema 1
summary: How pysos_sysml lowers its IR to the schema-1 manifest owned by pysos_coordinate, including launch timeout and producer env, and how determinism and the round trip are protected.
date: 2026-11-23
status: current
---

# Execution Manifest, Schema 1

The manifest schema is **owned by `pysos_coordinate`**, not by this package. Its
normative definition is
[`pysos_coordinate/docs/breakdown/02-architecture/manifest.md`](https://github.com/pyssporg/pysos_coordinate/blob/main/docs/breakdown/02-architecture/manifest.md).
`pysos_sysml.lower` targets that schema and documents its mapping here; it does
not import the owner and does not execute the result.

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
`telemetry`, `control`, and `startup_timeout`.

## Mapping

| Manifest field | Source and conversion |
| --- | --- |
| `schema` | constant `1` (`pysos_sysml.lower.SCHEMA_VERSION`) |
| `name` | package name (`FederationDef.name`) |
| `timing` | constant `"wall_clock"` (`pysos_sysml.lower.TIMING_POLICY`) |
| `instances[].name` | instance name, or `<name>_<i>` when multiplicity > 1 |
| `instances[].command` | `command` String tokenized to argv with `shlex.split`; no shell runs |
| `instances[].cwd` | `cwd` String |
| `instances[].env` | producer-owned channel: occurrence ports as decimal text, plus `PYSOS_SCENARIO` when authored plus `PYSOS_LAUNCH_MODE`, `PYSOS_READINESS`, `PYSOS_LAUNCH_ORDER` and `PYSOS_AFTER_PROCESS` when a launch is authored |
| `instances[].entities` | one `EntityDef`: `site`, `application`, `entity` as decimal text, plus `marking` |
| `instances[].telemetry` | one `EndpointDef`: `host`, `port` only |
| `instances[].control` | one `EndpointDef`: `host`, `port` only |
| `instances[].startup_timeout` | authored `launch.timeout_s` when present, else the reserved default `30.0` |

The SysML attributes `site`, `application`, and `entity` are `Integer`, but the
manifest's `EntityRef` identity is text, so lowering emits their decimal spelling.
`command` is authored as one String and becomes an argv list before it crosses
the boundary; quoting is handled by `shlex.split`, and shell operators are
literal tokens because no shell is involved. The IR keeps `EndpointDef.name`
(the telemetry/control channel), but the manifest endpoint has no name field.

One manifest instance is one process occurrence. Its entity id and both ports
are the occurrence's arithmetic values from
`02-architecture/sysml-subset.md`, so a three-occurrence instance produces
three entries, each with one entity and one endpoint per channel. The IR keeps
the resolved aircraft definition (for example `Aircraft::AircraftModel`) and
the launch, but neither adds a manifest key beyond the env values above.

## Environment contract

`env` is the producer-owned channel from the authored setup to the launched
producer process. Lowering always emits exactly these string-to-string keys per
occurrence:

| Key | Value | Present |
| --- | --- | --- |
| `PYSOS_TELEMETRY_PORT` | occurrence telemetry port, decimal text | always |
| `PYSOS_CONTROL_PORT` | occurrence control port, decimal text | always |
| `PYSOS_SCENARIO` | authored `scenario` value, verbatim | only when authored |
| `PYSOS_LAUNCH_MODE` | authored `launch.mode` value, verbatim | only when a launch is authored |
| `PYSOS_READINESS` | authored `launch.readiness` value, verbatim | only when a launch is authored |

The scenario and launch are authored once per part usage, so every occurrence
of that usage carries the same values; the two port keys differ per occurrence.
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
match, and treats drift (including a missing file) as exit 1 with a short
stderr message plus a unified diff bounded to 20 lines. Usage errors and
`SysMLError` keep exit 2.
