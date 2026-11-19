import ast
import json
from pathlib import Path

import pytest

import pysos_sysml.lower
from pysos_sysml.loader import load_federation
from pysos_sysml.lower import dump_manifest, manifest_json, to_manifest
from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef

FIXTURE = Path(__file__).parent / "fixtures" / "federation.sysml"


def _env(port, scenario=None):
    env = {
        "PYSOS_TELEMETRY_PORT": str(port),
        "PYSOS_CONTROL_PORT": str(port + 1000),
    }
    if scenario is not None:
        env["PYSOS_SCENARIO"] = scenario
    return env


def _instance(name, port, entity, command, cwd, site, application):
    return {
        "name": name,
        "command": command,
        "cwd": cwd,
        "env": _env(port),
        "entities": [
            {
                "site": str(site),
                "application": str(application),
                "entity": str(entity),
                "marking": "UNCLASSIFIED",
            }
        ],
        "telemetry": [{"port": port, "host": "127.0.0.1"}],
        "control": [{"port": port + 1000, "host": "127.0.0.1"}],
        "startup_timeout": 30.0,
    }


@pytest.mark.level_contract
def test_manifest_matches_schema_one_exactly():
    assert to_manifest(load_federation(FIXTURE)) == {
        "schema": 1,
        "name": "Soc",
        "timing": "wall_clock",
        "instances": [
            _instance("sensor_1", 5100, 100, ["sensor-agent"], "/opt/sensor", 2, 7),
            _instance("sensor_2", 5101, 101, ["sensor-agent"], "/opt/sensor", 2, 7),
            _instance("sensor_3", 5102, 102, ["sensor-agent"], "/opt/sensor", 2, 7),
            _instance("gateway", 5200, 200, ["gateway"], "/opt/gateway", 1, 9),
        ],
    }


@pytest.mark.level_contract
def test_occurrence_expansion_and_producer_env():
    manifest = to_manifest(load_federation(FIXTURE))
    assert manifest["schema"] == 1
    assert manifest["name"] == "Soc"
    assert manifest["timing"] == "wall_clock"
    assert [entry["name"] for entry in manifest["instances"]] == [
        "sensor_1",
        "sensor_2",
        "sensor_3",
        "gateway",
    ]
    assert [entry["env"] for entry in manifest["instances"]] == [
        _env(5100),
        _env(5101),
        _env(5102),
        _env(5200),
    ]
    assert all(
        isinstance(entry["command"], list) for entry in manifest["instances"]
    )


def _federation(instance):
    return FederationDef(name="Soc", instances=[instance])


def _node(**overrides):
    values = {
        "name": "node",
        "part_def": "Node",
        "count": 1,
        "entities": [EntityDef(site=1, application=1, entity=1, marking="U")],
        "telemetry_ports": [EndpointDef(name="telemetry", port=1)],
        "control_ports": [EndpointDef(name="control", port=2)],
        "command": "run",
        "cwd": "/",
    }
    values.update(overrides)
    return InstanceDef(**values)


@pytest.mark.level_unit
def test_authored_scenario_reaches_every_occurrence_env():
    federation = _federation(
        _node(
            count=2,
            entities=[
                EntityDef(site=1, application=1, entity=1, marking="U"),
                EntityDef(site=1, application=1, entity=2, marking="U"),
            ],
            telemetry_ports=[
                EndpointDef(name="telemetry", port=5000),
                EndpointDef(name="telemetry", port=5001),
            ],
            control_ports=[
                EndpointDef(name="control", port=6000),
                EndpointDef(name="control", port=6001),
            ],
            scenario="cruise",
        )
    )
    envs = [entry["env"] for entry in to_manifest(federation)["instances"]]
    assert envs == [_env(5000, "cruise"), _env(5001, "cruise")]
    assert [env["PYSOS_SCENARIO"] for env in envs] == ["cruise", "cruise"]


@pytest.mark.level_unit
def test_scenario_absent_emits_no_scenario_key():
    env = to_manifest(_federation(_node()))["instances"][0]["env"]
    assert env == {
        "PYSOS_TELEMETRY_PORT": "1",
        "PYSOS_CONTROL_PORT": "2",
    }
    assert "PYSOS_SCENARIO" not in env


@pytest.mark.level_unit
def test_scenario_lowering_is_deterministic():
    federation = _federation(_node(scenario="descent"))
    first = manifest_json(federation)
    second = manifest_json(federation)
    assert first == second
    assert first == json.dumps(to_manifest(federation), sort_keys=True, indent=2) + "\n"
    assert '"PYSOS_SCENARIO": "descent"' in first


@pytest.mark.level_component
def test_json_is_deterministic_and_dump_writes_the_same_text(tmp_path):
    federation = load_federation(FIXTURE)
    text = manifest_json(federation)
    assert text == json.dumps(to_manifest(federation), sort_keys=True, indent=2) + "\n"
    assert text.index('  "instances"') < text.index('  "schema"')
    assert text.endswith("\n")
    target = tmp_path / "out.json"
    dump_manifest(federation, target)
    assert target.read_text(encoding="utf-8") == text


@pytest.mark.level_unit
def test_misaligned_occurrence_lists_are_a_programming_error():
    federation = FederationDef(
        name="Soc",
        instances=[
            InstanceDef(
                name="node",
                part_def="Node",
                count=2,
                entities=[EntityDef(site=1, application=1, entity=1, marking="U")],
                telemetry_ports=[EndpointDef(name="telemetry", port=1)],
                control_ports=[EndpointDef(name="control", port=2)],
                command="run",
                cwd="/",
            )
        ],
    )
    with pytest.raises(ValueError, match="count 2 but has 1 entities"):
        to_manifest(federation)


@pytest.mark.level_unit
def test_command_string_becomes_argv_without_a_shell():
    federation = FederationDef(
        name="Soc",
        instances=[
            InstanceDef(
                name="node",
                part_def="Node",
                count=1,
                entities=[EntityDef(site=1, application=1, entity=1, marking="U")],
                telemetry_ports=[EndpointDef(name="telemetry", port=1)],
                control_ports=[EndpointDef(name="control", port=2)],
                command='run --label "two words"',
                cwd="/",
            )
        ],
    )
    assert to_manifest(federation)["instances"][0]["command"] == [
        "run",
        "--label",
        "two words",
    ]


@pytest.mark.level_unit
def test_empty_command_is_rejected_after_tokenizing():
    federation = FederationDef(
        name="Soc",
        instances=[
            InstanceDef(
                name="node",
                part_def="Node",
                count=1,
                entities=[EntityDef(site=1, application=1, entity=1, marking="U")],
                telemetry_ports=[EndpointDef(name="telemetry", port=1)],
                control_ports=[EndpointDef(name="control", port=2)],
                command="   ",
                cwd="/",
            )
        ],
    )
    with pytest.raises(ValueError, match="command must not be empty"):
        to_manifest(federation)


@pytest.mark.level_static
def test_lowering_never_imports_the_schema_owner():
    tree = ast.parse(Path(pysos_sysml.lower.__file__).read_text(encoding="utf-8"))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    forbidden = {"pysos_coordinate", "pysos_simulate"}
    assert not [name for name in modules if name.split(".")[0] in forbidden]
