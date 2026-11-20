---
id: INFO-002
type: info
title: Layers, Import Rules, And The Parser Boundary
summary: Module responsibilities, the one-way imports, and the pycps_sysml2 multiplicity gap.
date: 2026-11-19
status: current
---

# Layers And Import Rules

## Modules

| Module | Responsibility | May import | Must not import |
| --- | --- | --- | --- |
| `pysos_sysml.model` | setup IR: four plain dataclasses | stdlib | `pycps_sysml2`, `pysos_coordinate`, anything else |
| `pysos_sysml.loader` | call `pycps_sysml2.load`, enforce the subset | stdlib, `pycps_sysml2`, `model` | `pysos_coordinate` |
| `pysos_sysml.lower` | IR → schema-1 manifest dict / JSON | stdlib, `model` | `pycps_sysml2`, `pysos_coordinate` |
| `pysos_sysml.cli` | `validate` and `manifest` commands | stdlib, `loader`, `lower` | anything else |

The IR is the stable center: the loader may know the parser, the lowerer may
know the manifest schema, but neither leaks the other's vocabulary into
`model`.

## Parser boundary

`pycps_sysml2.load(path)` returns an `Architecture`: package name, ordered part
definitions, and per-definition attributes, ports, parts, connections, and
bindings. The loader walks only that public model. It does not import
`pycps_sysml2.model.parser` and does not read sysmlpy trees.

Definition-level attributes are normalized by `pycps_sysml2`; attribute
usages inside an anonymous part-usage body keep their **source text** as
`Attribute.value` (`'2'`, `'"UNCLASSIFIED"'`). The loader performs the literal
conversion and rejects anything that is not an integer or a quoted string.

## pycps_sysml2 0.3.0 gap: part-usage multiplicity

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
