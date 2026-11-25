# pysos-sysml

System-of-systems simulation setup in SysML v2, lowered to an execution
manifest.

`pysos-sysml` reads one setup file, builds a small self-contained IR, and emits
the schema-1 manifest owned by `pysos_coordinate`. It is a thin layer over
[`pycps_sysml`](https://github.com/pyssporg/pycps_sysml): one parser, one
documented subset, no artifacts, no execution.

## Install

Python 3.11 or newer.

```bash
python -m pip install -e ".[dev]"
python -m pip install -e "repos/pysos_sysml[dev]"   # from the workspace root
```

The runtime dependency is the pinned `pycps_sysml` 0.4.0 wheel, fetched from
its GitHub release:

```text
https://github.com/pyssporg/pycps_sysml/releases/download/v0.4.0/pycps_sysml-0.4.0-py3-none-any.whl
```

## Use

```bash
pysos-sysml validate tests/fixtures/federation.sysml
pysos-sysml manifest tests/fixtures/federation.sysml -o manifest.json
pysos-sysml manifest tests/fixtures/federation.sysml   # stdout
pysos-sysml manifest tests/fixtures/two_instances.sysml \
  -o tests/fixtures/two_instances.manifest.json --check
pysos-sysml manifest tests/fixtures/aircraft_federation.sysml \
  --include tests/fixtures/aircraft.sysml -o manifest.json
```

```text
federation: Soc
instances: 2
occurrences: 4
entities: 4
telemetry endpoints: 4
control endpoints: 4
```

`--include PATH` is repeatable on both `validate` and `manifest`; it adds a
vocabulary or architecture root to the primary setup. The bundled
`PysosSoS::LaunchSpec` vocabulary is always included and needs only
`private import PysosSoS::*;` in the setup. `--check` requires `-o/--output`
and compares the current lowering with that file byte for byte, without writing
it. A match prints
`ok: PATH is up to date` and exits 0. Drift exits 1 with a short stderr message
and a bounded unified diff (at most 20 lines); a missing file exits 1 with a
short stderr message and no diff.

Library use:

```python
from pysos_sysml import check, dump_manifest, load_federation, render, sos_definitions, to_manifest

federation = load_federation("federation.sysml")
with_aircraft = load_federation("aircraft_federation.sysml", includes=("aircraft.sysml",))
assert sos_definitions().is_file()        # bundled PysosSoS vocabulary
manifest = to_manifest(federation)
dump_manifest(federation, "manifest.json")
text = render("federation.sysml")       # current lowering as text
current = check("federation.sysml", "manifest.json")  # byte comparison
```

## Setup subset

A primary `package` imports vocabulary, declares composition `part def`s, and
one `part def Federation` whose `part` usages are the instances. Included roots
supply architecture such as the aircraft model; a composition records its
`aircraft` and instances may carry the bundled launch vocabulary:

```sysml
package Flight {
  private import Aircraft::*;
  private import PysosSoS::*;

  part def AircraftEntity {
    part aircraft : AircraftModel;
  }

  part def Federation {
    part jet : AircraftEntity [3] {
      attribute site : Integer = 3;
      attribute application : Integer = 4;
      attribute entity : Integer = 300;
      attribute marking : String = "UNCLASSIFIED";
      attribute telemetryPort : Integer = 5300;
      attribute controlPort : Integer = 6300;
      attribute command : String = "jet-engine";
      attribute cwd : String = "/opt/jet";
      part launch : LaunchSpec {
        attribute mode : String = "supervised";
        attribute readiness : String = "port_bound";
        attribute timeout_s : Real = 12.5;
        attribute order : Integer = 2;
        attribute after_process : String = "supervisor";
      }
    }
  }
}
```

`[3]` means three occurrences with consecutive entity ids and ports. The launch
timeout becomes the manifest `startup_timeout`; its mode, readiness, order and
after-process become producer environment keys. Readiness is one of `none`,
`port_bound`, `socket_bound`, or `log_line`. A participant's transport parameter
set may declare `transport = "udp"` (`host:port` addresses) or
`transport = "unix"` (bare absolute paths or `@name`); Unix lowers to a schema-2
endpoint and `PYSOS_TRANSPORT` / `PYSOS_TELEMETRY_PATH` env keys. The complete accepted language,
its values, and its errors are in
[`docs/breakdown/02-architecture/sysml-subset.md`](docs/breakdown/02-architecture/sysml-subset.md).
Anything outside it raises `SysMLError` naming the offending qualified name.

## Manifest

Schema version 1 is owned by `pysos_coordinate`, whose
[`manifest leaf`](https://github.com/pyssporg/pysos_coordinate/blob/main/docs/breakdown/02-architecture/manifest.md)
is the normative contract. `pysos_sysml` conforms without importing it; the
lowering and its conversions are documented in
[`docs/breakdown/02-architecture/manifest.md`](docs/breakdown/02-architecture/manifest.md).
Output is deterministic: sorted keys, two-space indent, one trailing newline.

The `[dev]` extra includes `pysos-coordinate`, so `python -m pytest` also runs
the round-trip test against the owner. Without it that test skips.

## Development

```bash
python -m pytest
ruff check src tests
```

Layout: `src/pysos_sysml/{model,loader,lower,manifest,cli}.py` plus the bundled
`src/pysos_sysml/sos.sysml`, tests under `tests/`.
Read [`AGENTS.md`](AGENTS.md) and the
[intent](docs/breakdown/00-intent/intent.md) before changing behaviour.

## License

MIT.
