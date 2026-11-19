---
id: INFO-003
type: info
title: Supported SysML v2 Subset
summary: The complete accepted setup language, its values, multiplicity semantics, and errors.
date: 2026-11-19
status: current
---

# Supported SysML v2 Subset

This is the whole language `pysos_sysml.loader` accepts. It is a setup
dialect, not general SysML. Everything not listed here is rejected with
`SysMLError`; there is no permissive mode and no silent drop.

## Grammar sketch

```sysml
package <Package> {
  part def <EntityType> {
  }

  part def Federation {
    part <instance> : <EntityType> [<N>]? {
      attribute site          : Integer = <integer>;
      attribute application   : Integer = <integer>;
      attribute entity        : Integer = <integer>;
      attribute marking       : String  = "<string>";
      attribute telemetryPort : Integer = <integer>;
      attribute controlPort   : Integer = <integer>;
      attribute command       : String  = "<string>";
      attribute cwd           : String  = "<string>";
    }
  }
}
```

`[]` marks an optional token. `<N>` and `<integer>` are decimal integer
literals; `<Package>`, `<EntityType>`, and `<instance>` are simple identifiers
(`[A-Za-z_][A-Za-z0-9_]*`).

## Rules

1. **One package, one file.** The package name is the federation name. Imports,
   included roots, and several packages are outside the subset.
2. **Exactly one `part def Federation`.** It carries the instance usages and
   nothing else: no attributes, ports, connections, bindings, constraints,
   specialization, or variation.
3. **Entity part defs are empty.** Every other `part def` is only a type for an
   instance; it declares no members. At least one instance must exist.
4. **Every instance is a `part` usage on `Federation`, typed by a declared part
   def.** The type must resolve; an unknown type is an error.
5. **An instance body carries exactly the eight attributes above**, all with
   their declared type and a literal value. Missing, unknown, untyped, or
   wrongly typed attributes are errors. Bodies contain no nested parts,
   connections, bindings, ports, or constraints.
6. **Multiplicity is one positive integer on the declaration line.** `[3]`
   expands to three occurrences; an omitted annotation means one occurrence.
   Ranges (`[2..4]`), unbounded (`[0..*]`), and zero are rejected.
7. **No other definitions.** `port def`, `attribute def`, `requirement def`, and
   `constraint def` are rejected, as are variation, specialization, metadata,
   and views.

## Value semantics

| Attribute | Type | Value |
| --- | --- | --- |
| `site` | `Integer` | decimal integer |
| `application` | `Integer` | decimal integer |
| `entity` | `Integer` | base entity id; occurrence *i* gets `entity + i` |
| `marking` | `String` | quoted string, escapes decoded |
| `telemetryPort` | `Integer` | base port; occurrence *i* gets `telemetryPort + i` |
| `controlPort` | `Integer` | base port; occurrence *i* gets `controlPort + i` |
| `command` | `String` | executable command line |
| `cwd` | `String` | working directory |

Occurrences are zero-based for arithmetic and one-based for names:
`part sensor : Sensor [3]` yields `sensor_1`, `sensor_2`, `sensor_3` with entity
ids `entity + 0`, `entity + 1`, `entity + 2`. A scalar instance keeps its bare
name.

## Errors

`SysMLError` is a `ValueError` carrying the source `path`. Messages name the
offender as `<Package>::Federation::<instance>::<attribute>`, or
`<Package>::<definition>` for a top-level definition. A file the parser cannot
parse raises `SysMLError` with the path and the parser's message; it is never
returned as a partial model.

## Example

`tests/fixtures/federation.sysml` is the reference input: package `Soc`, two
entity part defs, a three-occurrence `sensor`, and a scalar `gateway`, each with
both ports.
