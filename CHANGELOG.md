# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Reconciled `lower.to_manifest` with the schema owned by `pysos_coordinate`:
  added top-level `name` and `timing`; emit `command` as an argv list tokenized
  with `shlex.split`; emit `site`, `application`, and `entity` as text; emit
  endpoints as `host`/`port` only; emit the reserved `startup_timeout` default.
  The strict multiplicity alignment check is unchanged.
- Documentation now names `pysos_coordinate` as the schema owner and points at
  its normative manifest leaf instead of describing a second owner.

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
