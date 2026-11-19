---
id: INFO-004
type: info
title: Execution Manifest, Schema 1
summary: The exact dictionary pysos_sysml lowers to, the schema version it targets, and determinism.
date: 2026-11-19
status: current
---

# Execution Manifest, Schema 1

`pysos_simulate` owns the manifest schema. `pysos_sysml` targets **schema
version 1** and documents it here; it does not import the owner and does not
execute the result.

## Shape

```json
{
  "schema": 1,
  "instances": [
    {
      "name": "sensor_1",
      "command": "sensor-agent",
      "cwd": "/opt/sensor",
      "env": {},
      "entities": [
        {"site": 2, "application": 7, "entity": 100, "marking": "UNCLASSIFIED"}
      ],
      "telemetry": [{"name": "telemetry", "port": 5100, "host": "127.0.0.1"}],
      "control": [{"name": "control", "port": 6100, "host": "127.0.0.1"}]
    }
  ]
}
```

Every manifest entry has exactly these keys: `name`, `command`, `cwd`, `env`,
`entities`, `telemetry`, `control`. The top level has exactly `schema` and
`instances`.

## Mapping

| Manifest field | Source |
| --- | --- |
| `schema` | constant `1` (`pysos_sysml.lower.SCHEMA_VERSION`) |
| `instances[].name` | instance name, or `<name>_<i>` when multiplicity > 1 |
| `instances[].command` | `command` attribute |
| `instances[].cwd` | `cwd` attribute |
| `instances[].env` | reserved, `{}` in 0.1.0 |
| `instances[].entities` | one `EntityDef`: `site`, `application`, `entity`, `marking` |
| `instances[].telemetry` | one `EndpointDef`: `name`, `port`, `host` |
| `instances[].control` | one `EndpointDef`: `name`, `port`, `host` |

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
