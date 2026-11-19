# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-19

### Added

- `pysos_sysml.model`: self-contained `FederationDef`, `InstanceDef`,
  `EntityDef`, and `EndpointDef` dataclasses.
- `pysos_sysml.loader`: `load_federation` over `pycps_sysml2.load`, with the
  documented setup subset enforced and `SysMLError` for everything else.
- `pysos_sysml.lower`: schema-1 manifest lowering and deterministic JSON dump.
- `pysos-sysml` CLI with `validate` and `manifest` commands.
- Architecture leaves for the layers, the SysML subset, and manifest schema 1.
