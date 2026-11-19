# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-11-19

### Changed

- Development dependency on the schema owner pinned to the
  `pysos_coordinate` 0.3.0 release wheel; the lowering itself is unchanged.

## [0.2.0] - 2026-11-19

### Added

- Optional `scenario : String` attribute on a `Federation` part usage. It is
  one authored value per usage and applies to every occurrence; unknown
  attributes are still rejected.
- `InstanceDef.scenario: str | None` in the setup IR.
- Producer environment channel in each lowered occurrence: `env` now always
  carries `PYSOS_TELEMETRY_PORT` and `PYSOS_CONTROL_PORT` as decimal text, plus
  `PYSOS_SCENARIO` when a scenario is authored. `pysos_coordinate` continues to
  pass `env` through opaquely as a string-to-string map.

### Changed

- Regenerated `tests/fixtures/two_instances.manifest.json`; its `env` is no
  longer empty.
- Documented the environment contract in
  `docs/breakdown/02-architecture/manifest.md` and extended the SysML subset
  leaf with the optional attribute and a two-usage example.

## [0.1.1] - 2026-11-19

### Changed

- Reconciled `lower.to_manifest` with schema **version 1** owned by
  `pysos_coordinate`: added top-level `name` and `timing`; emit `command` as an
  argv list tokenized with `shlex.split`; emit `site`, `application`, and
  `entity` as text (string entity ids); emit endpoints as `host`/`port` only;
  emit the reserved `startup_timeout` default. The strict multiplicity
  alignment check is unchanged.
- Documentation now names `pysos_coordinate` as the schema owner and points at
  its normative manifest leaf instead of describing a second owner.
- The optional `[dev]` dependency on `pysos-coordinate` is pinned to the v0.2.1
  release wheel instead of a Git checkout, so the cross-repo round-trip is
  reproducible.

### Added

- Optional `[dev]` dependency on `pysos-coordinate` and a round-trip test that
  parses the checked-in two-instance lowering through the owner's public API and
  validation/port CLI. It skips cleanly when the owner is absent.

## [0.1.0] - 2026-11-19

### Added

- `pysos_sysml.model`: self-contained `FederationDef`, `InstanceDef`,
  `EntityDef`, and `EndpointDef` dataclasses.
- `pysos_sysml.loader`: `load_federation` over `pycps_sysml2.load`, with the
  documented setup subset enforced and `SysMLError` for everything else.
- `pysos_sysml.lower`: schema-1 manifest lowering and deterministic JSON dump.
- `pysos-sysml` CLI with `validate` and `manifest` commands.
- Architecture leaves for the layers, the SysML subset, and manifest schema 1.
