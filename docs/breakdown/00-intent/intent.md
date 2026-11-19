---
id: INFO-001
type: info
title: Intent
summary: Why pysos_sysml exists, what it commits to, and what it refuses to become.
date: 2026-11-19
status: current
---

# Intent

## Purpose

`pysos_sysml` defines a **system-of-systems simulation setup** in SysML v2 and
lowers it to an execution manifest. A setup names the instances that make up the
federation, the simulation identity each instance joins, and the telemetry and
control endpoints it uses.

The package is deliberately thin:

```text
federation.sysml --pycps_sysml2.load--> Architecture
                                           │
                                  pysos_sysml.loader
                                           │
                                    FederationDef
                                           │
                                  pysos_sysml.lower
                                           │
                                  manifest (schema 1)
```

It is the third package of the `pysos_*` family and the only one that reads the
setup language. It emits data; it does not run anything.

## Commitments

- **One parser.** SysML v2 is parsed by `pycps_sysml2.load`. This package owns
  no grammar, no tokenizer, and no second dialect.
- **The subset is documented and enforced.** `02-architecture/sysml-subset.md`
  is the complete accepted language. Anything outside it raises `SysMLError`
  with the offending qualified name; nothing is ignored.
- **The IR is self-contained.** `pysos_sysml.model` is plain dataclasses with
  no dependency on an execution package. The manifest dictionary is the only
  cross-package contract.
- **Lowering is pure and deterministic.** `to_manifest` reads the IR and
  returns data. `dump_manifest` sorts keys, indents by two spaces, and ends with
  one newline.
- **The manifest schema is owned elsewhere.** `pysos_coordinate` owns schema 1;
  this package targets it and documents the version it emits.

## Non-goals

- **Not a parser fork.** No grammar change, no private parse-tree traversal, no
  "temporary" second dialect.
- **Not an artifact generator.** No SSP, SSD, FMU, or Modelica output.
- **Not a runner.** No process launch, scheduling, transport, or execution.
- **Not a workflow engine.** Sequencing and orchestration belong to the
  execution side of the family.
- **Not a general SysML tool.** Only the setup subset in
  `02-architecture/sysml-subset.md` is accepted.

## Roles in the ecosystem

| Package | Responsibility | Relationship |
| --- | --- | --- |
| `pycps_sysml2` | SysML v2 dialect parser and architecture IR | direct dependency, pinned wheel |
| `pysos_sysml` | setup IR, loader, manifest lowering, CLI | this package |
| `pysos_coordinate` | owns manifest schema 1 and executes it | consumer of the manifest |

The arrows are one-way: `pysos_sysml` imports `pycps_sysml2`, never the
reverse, and never imports `pysos_coordinate`.
