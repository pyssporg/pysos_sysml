---
id: INFO-003
type: info
title: Supported SysML v2 Subset
summary: The complete accepted setup language, its values, multiplicity semantics, imports, includes, and errors.
date: 2026-11-23
status: current
---

# Supported SysML v2 Subset

This is the whole language `pysos_sysml.loader` accepts. It is a setup
dialect, not general SysML. Everything not listed here is rejected with
`SysMLError`; there is no permissive mode and no silent drop.

## Grammar sketch

```sysml
package <Package> {
  [private import <Vocabulary>::*; ...]

  part def <EntityType> {
    [part <composition> : <Type>; ...]   // at most one named aircraft
  }

  part def Federation {
    part <instance> : <EntityType> [<N>]? {
      attribute site          : Integer = <integer>;
      attribute application   : Integer = <integer>;
      attribute entity        : Integer = <integer>;
      attribute marking       : String  = "<string>";
      attribute telemetryPort : Integer = <integer>;
      [attribute controlPort : Integer = <integer>;]
      attribute command       : String  = "<string>";
      attribute cwd           : String  = "<string>";
      [attribute scenario : String = "<string>";]
      [part launch : LaunchSpec {
        attribute mode          : String  = "<mode>";
        attribute readiness     : String  = "<readiness>";
        attribute timeout_s     : Real    = <real>;
        attribute order         : Integer = <integer>;
        attribute after_process : String  = "<process-or-role>" | "";
      }]
    }
  }
}
```

`[]` marks an optional token. `<N>` and `<integer>` are decimal integer
literals; `<real>` is a decimal real literal; `<Package>`, `<EntityType>`,
`<Type>`, and `<instance>` are simple identifiers
(`[A-Za-z_][A-Za-z0-9_]*`, qualified names allowed for imported types).

## Rules

1. **One primary package and file.** The package name is the federation name.
   The primary model declares exactly one package; imports are accepted and
   every type still has to resolve through them (see rule 8). Included roots
   are separate files passed to the loader.
2. **Exactly one primary `part def Federation`.** It carries the instance
   usages and nothing else: no attributes, ports, connections, bindings,
   constraints, specialization, or variation. A `Federation` supplied only by
   an included root is not a primary definition.
3. **Composition part defs declare only typed part usages.** Every other
   `part def` in the primary model may declare `part <name> : <Type>` usages
   (at most one named `aircraft`) and nothing else: no attributes, ports,
   connections, bindings, constraints, usage bodies, specialization, or
   variation. Each type must resolve. An `aircraft` usage records the resolved
   stored key (for example `Aircraft::AircraftModel`) on the instance IR.
   At least one instance must exist.
4. **Every instance is a `part` usage on `Federation`, typed by a part def.**
   The type must resolve; an unknown type is an error.
5. **An instance body carries the seven required attributes above, plus the
   optional `controlPort` and at most the optional `scenario`,** all with their
   declared type and a literal value.
   Missing, unknown, untyped, or wrongly typed attributes are errors. Bodies
   contain no connections, bindings, ports, or constraints.
6. **At most one nested `part launch : LaunchSpec` per instance.** It must
   resolve to a part def named `LaunchSpec` declaring exactly `mode : String`,
   `readiness : String`, `timeout_s : Real`, `order : Integer`, and
   `after_process : String`. The usage authors exactly those five attributes as
   literals, once each; duplicates, unknown names, missing names, and wrong
   types are errors. `mode` is one of `supervised`, `operator`, `manual`;
   `readiness` is one of `none`, `port_bound`, `log_line`; the timeout is
   greater than zero; `order` is non-negative; `after_process` is empty or a
   process/role identifier. Any other nested part is rejected. The vocabulary
   also ships `part def Application` (roles, command, cwd and a nested launch);
   host-side models specialize it, the setup subset itself does not.
7. **Multiplicity is one positive integer on the declaration line.** `[3]`
   expands to three occurrences; an omitted annotation means one occurrence.
   Ranges (`[2..4]`), unbounded (`[0..*]`), and zero are rejected.
8. **Vocabulary and architecture come from included roots.** A qualified
   definition is usable only through an import of its package
   (`private import Aircraft::*;`). Included roots are exempt from the primary
   member checks: they may declare port/attribute/requirement/constraint defs,
   specialization, ports, and connections. They may not redefine a definition
   the primary model or another root already supplies. A primary `attribute
   def` is accepted only as a parameter set: its specialization chain must
   reach the shipped `PysspCore::ParameterSet` marker by definition identity,
   not by name; a missing core root is an error naming that root.
9. **No other primary definitions.** `port def`, `requirement def`,
   `constraint def`, variation, specialization, metadata, and views are
   rejected in the primary model, except the `attribute def` parameter sets in
   rule 8. Only included roots may carry the rest.

## Value semantics

| Attribute | Type | Value |
| --- | --- | --- |
| `site` | `Integer` | decimal integer |
| `application` | `Integer` | decimal integer |
| `entity` | `Integer` | base entity id; occurrence *i* gets `entity + i` |
| `marking` | `String` | quoted string, escapes decoded |
| `telemetryPort` | `Integer` | base port; occurrence *i* gets `telemetryPort + i` |
| `controlPort` | `Integer` | optional base port; occurrence *i* gets `controlPort + i`; omitted means no control endpoint |
| `command` | `String` | executable command line |
| `cwd` | `String` | working directory |
| `scenario` | `String` | optional flight scenario; same value for every occurrence |
| `launch.mode` | `String` | `supervised`, `operator`, or `manual` |
| `launch.readiness` | `String` | `none`, `port_bound`, or `log_line` |
| `launch.timeout_s` | `Real` | launch timeout in seconds; greater than zero |
| `launch.order` | `Integer` | launch phase; lower starts first; non-negative |
| `launch.after_process` | `String` | process name or role that must be ready first; empty means none |

`scenario` is optional and unrelated to multiplicity: one authored value
applies to every occurrence of the usage. Its literal follows the same rule as
`command` (quoted string, escapes decoded).

Occurrences are zero-based for arithmetic and one-based for names:
`part sensor : Sensor [3]` yields `sensor_1`, `sensor_2`, `sensor_3` with entity
ids `entity + 0`, `entity + 1`, `entity + 2`. A scalar instance keeps its bare
name.

## Errors

`SysMLError` is a `ValueError` carrying the source `path`. Messages name the
offender as `<Package>::Federation::<instance>::<attribute>`,
`<Package>::Federation::<instance>::launch::<attribute>`, or
`<Package>::<definition>` for a top-level definition. A file the parser cannot
parse raises `SysMLError` with the path and the parser's message; it is never
returned as a partial model.

## Example

`tests/fixtures/federation.sysml` is the reference input: package `Soc`, two
entity part defs, a three-occurrence `sensor`, and a scalar `gateway`, each with
both ports. Two usages may author different scenarios:

```sysml
part def Federation {
  part sensor : Sensor [2] {
    attribute site          : Integer = 2;
    attribute application   : Integer = 7;
    attribute entity        : Integer = 100;
    attribute marking       : String  = "UNCLASSIFIED";
    attribute telemetryPort : Integer = 5100;
    attribute controlPort   : Integer = 6100;
    attribute command       : String  = "sensor-agent";
    attribute cwd           : String  = "/opt/sensor";
    attribute scenario      : String  = "cruise";
  }

  part gateway : Gateway {
    attribute site          : Integer = 1;
    attribute application   : Integer = 9;
    attribute entity        : Integer = 200;
    attribute marking       : String  = "UNCLASSIFIED";
    attribute telemetryPort : Integer = 5200;
    attribute controlPort   : Integer = 6200;
    attribute command       : String  = "gateway";
    attribute cwd           : String  = "/opt/gateway";
    attribute scenario      : String  = "descent";
  }
}
```

Both `sensor` occurrences (`sensor_1`, `sensor_2`) carry `"cruise"`; `gateway`
carries `"descent"`.

`tests/fixtures/aircraft_federation.sysml` is the imported-architecture
reference. It imports `Aircraft::*` and the bundled `PysosSoS::*`, composes
`part aircraft : AircraftModel` inside `AircraftEntity`, and launches with the
shared vocabulary:

```sysml
package Flight {
  private import Aircraft::*;
  private import PysosSoS::*;

  part def AircraftEntity {
    part aircraft : AircraftModel;
  }

  part def Federation {
    part jet : AircraftEntity {
      attribute site          : Integer = 3;
      attribute application   : Integer = 4;
      attribute entity        : Integer = 300;
      attribute marking       : String  = "UNCLASSIFIED";
      attribute telemetryPort : Integer = 5300;
      attribute controlPort   : Integer = 6300;
      attribute command       : String  = "jet-engine";
      attribute cwd           : String  = "/opt/jet";
      part launch : LaunchSpec {
        attribute mode          : String  = "supervised";
        attribute readiness     : String  = "port_bound";
        attribute timeout_s     : Real    = 12.5;
        attribute order         : Integer = 2;
        attribute after_process : String  = "supervisor";
      }
    }
  }
}
```

Load it with `load_federation(path, includes=(Path("aircraft.sysml"),))` or
`--include aircraft.sysml`; the bundled `sos.sysml` is always included.
