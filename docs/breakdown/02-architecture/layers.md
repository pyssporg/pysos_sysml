---
id: INFO-002
type: info
title: Layers, Import Rules, And The Parser Boundary
summary: Module responsibilities, the one-way imports, the parser boundary, and the pycps_sysml2 multiplicity gap.
date: 2026-11-23
status: current
---

# Layers And Import Rules

## Modules

| Module | Responsibility | May import | Must not import |
| --- | --- | --- | --- |
| `pysos_sysml.model` | setup IR: five plain dataclasses | stdlib | `pycps_sysml2`, `pysos_coordinate`, anything else |
| `pysos_sysml.loader` | call `pycps_sysml2.load`, ship the launch vocabulary, enforce the subset | stdlib, `pycps_sysml2`, `model` | `pysos_coordinate` |
| `pysos_sysml.lower` | IR → schema-1 manifest dict / JSON | stdlib, `model` | `pycps_sysml2`, `pysos_coordinate` |
| `pysos_sysml.manifest` | `render` and `check`: lowering versus a checked-in file | stdlib, `loader`, `lower` | `pycps_sysml2`, `pysos_coordinate` |
| `pysos_sysml.cli` | `validate` and `manifest` commands | stdlib, `loader`, `lower`, `manifest` | anything else |

The IR is the stable center: the loader may know the parser, the lowerer may
know the manifest schema, but neither leaks the other's vocabulary into
`model`.

## Parser boundary

`pycps_sysml2.load(path, *includes)` returns an `Architecture`: package name,
ordered part definitions, per-definition attributes, ports, parts, connections,
and bindings, plus the import visibility map and the stored keys supplied by
included roots. The loader always passes the bundled `sos.sysml` as the first
included root, then any caller `--include` roots. It walks only that public
model. It does not import `pycps_sysml2.model.parser` and does not read sysmlpy
trees.

Definition-level attributes are normalized by `pycps_sysml2`; attribute
usages inside an anonymous part-usage body keep their **source text** as
`Attribute.value` (`'2'`, `'"UNCLASSIFIED"'`, `'12.5'`). The loader performs the
literal conversion with the standard library and rejects anything that is not
an integer, a quoted string, or a real literal. Nested launch values use the
same raw-text path.

Included roots are vocabulary and architecture: the loader skips them in the
primary definition and member checks but honours their import visibility.
`Architecture.resolve_part` remains the only name resolver.

## pycps_sysml2 0.4.0 gap: part-usage multiplicity

`PartUsage` has no `multiplicity` field. `Attribute` and `PortUsage` do, and
the parser has a `multiplicity()` helper, but `load` never reads it for a part
usage, so `part sensor : Sensor [3]` loses the `[3]` silently.

**Smallest extension needed:** add `multiplicity: str | None = None` to
`PartUsage` and set it in `_part_definition` with the existing
`multiplicity(part)` helper. That is a two-line change in `pycps_sysml2`; it
is not made here because the dependency is read-only.

**Read-only workaround:** `loader._multiplicities` scans physical lines for
`part <name> : <Type> [N]` and accepts only a positive integer. Structure,
names, types, and attribute values still come from the parser. A missing or
malformed annotation is not guessed at; a range, `*`, or conflicting count
raises `SysMLError`. The annotation must sit on the usage's declaration line,
which the documented subset requires.

When `pycps_sysml2` gains the field, the adjunct should be deleted and the
count read from `PartUsage.multiplicity`. The subset and manifest do not change.

## Validation adjunct: duplicate launch attributes

`pycps_sysml2` stores anonymous-body attributes in a dict, so a repeated
`attribute readiness : String = ...;` keeps the last value and drops the
earlier one. To keep "nothing is ignored", `loader._launch_duplicates` reads
only the primary `Federation` body, bounds each `part launch` block by brace
matching (quoted strings and comments skipped), and reports repeated attribute
names. It recovers no values and is not a second grammar; the parser still owns
structure, names, types, and values.

## Bundled vocabulary

`src/pysos_sysml/sos.sysml` is package data (`[tool.setuptools.package-data]`).
`pysos_sysml.SOS_FILE` names it and `pysos_sysml.sos_definitions()` returns its
real path, mirroring `pyssp_sysml_definitions.core_definitions()`. The loader
adds it as an include root on every load; a primary model still has to import
`PysosSoS::*` to see `LaunchSpec`.

## One-way dependencies

```text
pycps_sysml2 ──► pysos_sysml.loader ──► pysos_sysml.model
                                             ▲
                      pysos_sysml.lower ─────┘
                                             ▲
                      pysos_sysml.cli ───────┘
```

`tests/test_lower.py` asserts that lowering imports no `pysos_coordinate` module;
`tests/test_loader.py` exercises the parser boundary through the fixture.
