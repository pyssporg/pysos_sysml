# AGENTS

## Vision first (required)

Before you read code, edit files, or plan a change, read the project vision:

**`docs/breakdown/00-intent/intent.md`**

It states why this repository exists, what it commits to, and what it refuses to
become. It is the first document to read, not a reference of last resort.

- Read it in full before making any change to code, tests, docs, or artifacts.
- Judge every proposed change against it. If a change conflicts with the vision,
  its commitments, goals, or non-goals, stop and surface the conflict; do not
  implement it silently.
- If the work shows the long-term direction is wrong, change the vision
  deliberately first, then the code. Never let the repository drift away from
  its stated intent.

## Rules

1. **Don't assume. Surface tradeoffs.** If a contract is ambiguous, stop and say
   so rather than picking a behaviour silently.
2. **Minimum code that solves the problem.** Nothing speculative.
3. **Touch only what you must.** Clean up only your own mess.
4. **Define success criteria and verify.**

## Repository focus

`pysos_sysml` is the setup layer of the `pysos_*` family. It reads a SysML v2
federation declaration, builds `FederationDef` / `InstanceDef` / `EntityDef` /
`EndpointDef`, and lowers it to the schema-1 manifest owned by `pysos_simulate`.

- Modules: `model` (IR), `loader` (parser walk and subset enforcement), `lower`
  (manifest), `cli` (`validate`, `manifest`).
- It sits between the parser and the runner: `pycps_sysml2` below,
  `pysos_simulate` above.

## Hard constraints

- **One parser.** SysML v2 is parsed by `pycps_sysml2.load`. Do not fork a
  parser, copy grammar, import sysmlpy directly, or invent a second dialect.
  The only lexical supplement is the documented multiplicity adjunct in
  `loader._multiplicities`, and it must disappear when the parser exposes
  `PartUsage.multiplicity`.
- **No artifact generation.** No SSP, SSD, FMU, Modelica, or other simulation
  artifact is produced here.
- **No execution.** Do not launch processes, open sockets, schedule, or run a
  simulation. `lower` returns data.
- **The subset is documented and enforced.** `docs/breakdown/02-architecture/`
  `sysml-subset.md` is the complete accepted language. Anything outside it
  raises `SysMLError` with a qualified name and a path; nothing is ignored.
- **The IR is self-contained.** `pysos_sysml.model` imports only the standard
  library. Do not add `pysos_simulate` types to it.
- **Do not import `pysos_simulate`.** The schema-1 dictionary is the contract;
  the owner is documented, not imported.
- **`pycps_sysml2` is read-only.** If its API cannot express the subset,
  document the smallest extension in `02-architecture/layers.md` and work
  around it read-only.
- **Deterministic output.** Sorted keys, two-space indent, one trailing newline.

## Environment

- Python >= 3.10.
- Install: `python -m pip install -e ".[dev]"`.
- Tests: `python -m pytest` (pyproject sets `pythonpath = ["src"]`).
- Lint: `ruff check src tests` (line length 100, `py310`).

## Documentation

`docs/breakdown/` holds current state: intent in `00-intent/`, module shape,
subset, and manifest in `02-architecture/`. Update the leaf that owns a
contract before changing code that implements it.
