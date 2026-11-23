# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `pysos_sysml.sos.sysml`: bundled `PysosSoS::LaunchSpec` vocabulary, shipped
  as package data and exposed as `SOS_FILE` and `sos_definitions()`.
- `load_federation(path, *, includes=())` and repeatable
  `--include PATH` on `pysos-sysml validate` and `manifest`. Imports and
  included roots are accepted; included definitions are exempt from primary
  subset member checks while staying visible only through their import.
- Primary composition part defs may declare typed `part <name> : <Type>`
  usages; an `aircraft` usage records its resolved key on the IR.
- Optional nested `part launch : LaunchSpec` on an instance, validated against
  the shared five-attribute vocabulary (`mode`, `readiness`, `timeout_s`,
  `order`, `after_process`) and lowered to `startup_timeout` plus
  `PYSOS_LAUNCH_MODE`, `PYSOS_READINESS`, `PYSOS_LAUNCH_ORDER` and
  `PYSOS_AFTER_PROCESS`.
- `PysosSoS::Application` base definition (roles, command, cwd, nested launch)
  for host-side models that specialize it.
- `LaunchDef` and `InstanceDef.launch` / `InstanceDef.aircraft` in the IR.
- Fixtures and tests for aircraft composition, the bundled launch vocabulary,
  include forwarding, duplicate launch attributes, and the new error cases.

### Changed

- The documented subset now covers imports, included roots, composition part
  usages, and the launch vocabulary; primary-entity and included-root rules are
  stated separately.
- `manifest.render` and `manifest.check` accept the same `includes` keyword as
  the loader, so `--check` works with includes.

## [0.3.1] - 2026-11-22

### Changed

- Pin the `pycps-sysml2` runtime dependency to the v0.4.0 release asset; the
  lowering is unchanged.

## [0.3.0] - 2026-11-19

### Added

- `pysos-sysml manifest FILE -o PATH --check`: compares the current lowering
  with the checked-in file byte for byte, prints `ok: PATH is up to date` and
  exits 0 on a match, and exits 1 on drift (including a missing file) with a
  unified diff bounded to 20 lines. `--check` without `-o` is a usage error
  (exit 2); existing stdout and `-o` behaviour is unchanged.
- `pysos_sysml.manifest.render` and `check` helpers; `render` reuses
  `manifest_json`, so the formatting rules have one owner.
- CLI tests for exact match, stale content, a missing expected file, the usage
  error, and the checked-in fixture; library tests for the helpers.

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
