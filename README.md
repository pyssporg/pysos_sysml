# pysos-sysml

System-of-systems simulation setup in SysML v2, lowered to an execution
manifest.

`pysos-sysml` reads one setup file, builds a small self-contained IR, and emits
the schema-1 manifest owned by `pysos_simulate`. It is a thin layer over
[`pycps_sysml2`](https://github.com/pyssporg/pycps_sysml2): one parser, one
documented subset, no artifacts, no execution.

## Install

Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
```

The runtime dependency is the pinned `pycps_sysml2` 0.2.0 wheel, fetched from
its GitHub release:

```text
https://github.com/pyssporg/pycps_sysml2/releases/download/v0.2.0/pycps_sysml2-0.2.0-py3-none-any.whl
```

## Use

```bash
pysos-sysml validate tests/fixtures/federation.sysml
pysos-sysml manifest tests/fixtures/federation.sysml -o manifest.json
pysos-sysml manifest tests/fixtures/federation.sysml   # stdout
```

```text
federation: Soc
instances: 2
occurrences: 4
entities: 4
telemetry endpoints: 4
control endpoints: 4
```

Library use:

```python
from pysos_sysml import dump_manifest, load_federation, to_manifest

federation = load_federation("federation.sysml")
manifest = to_manifest(federation)
dump_manifest(federation, "manifest.json")
```

## Setup subset

A `package` contains empty entity `part def`s and one `part def Federation`
whose `part` usages are the instances:

```sysml
package Soc {
  part def Sensor {
  }

  part def Federation {
    part sensor : Sensor [3] {
      attribute site : Integer = 2;
      attribute application : Integer = 7;
      attribute entity : Integer = 100;
      attribute marking : String = "UNCLASSIFIED";
      attribute telemetryPort : Integer = 5100;
      attribute controlPort : Integer = 6100;
      attribute command : String = "sensor-agent";
      attribute cwd : String = "/opt/sensor";
    }
  }
}
```

`[3]` means three occurrences with consecutive entity ids and ports. The
complete accepted language, its values, and its errors are in
[`docs/breakdown/02-architecture/sysml-subset.md`](docs/breakdown/02-architecture/sysml-subset.md).
Anything outside it raises `SysMLError` naming the offending qualified name.

## Manifest

Schema version 1 is owned by `pysos_simulate`; `pysos_sysml` produces the
dictionary and documents the targeted version in
[`docs/breakdown/02-architecture/manifest.md`](docs/breakdown/02-architecture/manifest.md).
Output is deterministic: sorted keys, two-space indent, one trailing newline.

## Development

```bash
python -m pytest
ruff check src tests
```

Layout: `src/pysos_sysml/{model,loader,lower,cli}.py`, tests under `tests/`.
Read [`AGENTS.md`](AGENTS.md) and the
[intent](docs/breakdown/00-intent/intent.md) before changing behaviour.

## License

MIT.
