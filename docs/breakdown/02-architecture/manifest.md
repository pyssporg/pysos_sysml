---
id: INFO-004
type: info
title: Execution Manifest, Schema 1
summary: How pysos_sysml lowers its IR to the schema-1 manifest owned by pysos_coordinate, and how determinism and the round trip are protected.
date: 2026-11-19
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
      "env": {},
      "entities": [
        {"site": "1", "application": "10", "entity": "1", "marking": "UNCLASSIFIED"}
      ],
      "telemetry": [{"host": "127.0.0.1", "port": 5551}],
      "control": [{"host": "127.0.0.1", "port": 5651}],
      "startup_timeout": 30.0
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
| `instances[].env` | reserved, `{}` in 0.1.0 |
| `instances[].entities` | one `EntityDef`: `site`, `application`, `entity` as decimal text, plus `marking` |
| `instances[].telemetry` | one `EndpointDef`: `host`, `port` only |
| `instances[].control` | one `EndpointDef`: `host`, `port` only |
| `instances[].startup_timeout` | reserved default `30.0`; the subset has no such attribute |

The SysML attributes `site`, `application`, and `entity` are `Integer`, but the
manifest's `EntityRef` identity is text, so lowering emits their decimal spelling.
`command` is authored as one String and becomes an argv list before it crosses
the boundary; quoting is handled by `shlex.split`, and shell operators are
literal tokens because no shell is involved. The IR keeps `EndpointDef.name`
(the telemetry/control channel), but the manifest endpoint has no name field.

One manifest instance is one process occurrence. Its entity id and both ports
are the occurrence's arithmetic values from
`02-architecture/sysml-subset.md`, so a three-occurrence instance produces
three entries, each with one entity and one endpoint per channel.

`env` is reserved because the setup subset has no environment attributes. A
future schema revision, not a silent extra key, is how environment variables
would be added.

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
