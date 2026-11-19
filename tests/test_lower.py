import ast
import json
from pathlib import Path

import pytest

import pysos_sysml.lower
from pysos_sysml.loader import load_federation
from pysos_sysml.lower import dump_manifest, manifest_json, to_manifest
from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef

FIXTURE = Path(__file__).parent / "fixtures" / "federation.sysml"


def _instance(name, port, entity, command, cwd):
    return {
        "name": name,
        "command": command,
        "cwd": cwd,
        "env": {},
        "entities": [
            {
                "site": 2 if command == "sensor-agent" else 1,
                "application": 7 if command == "sensor-agent" else 9,
                "entity": entity,
                "marking": "UNCLASSIFIED",
            }
        ],
        "telemetry": [{"name": "telemetry", "port": port, "host": "127.0.0.1"}],
        "control": [{"name": "control", "port": port + 1000, "host": "127.0.0.1"}],
    }


@pytest.mark.level_contract
def test_manifest_matches_schema_one_exactly():
    assert to_manifest(load_federation(FIXTURE)) == {
        "schema": 1,
        "instances": [
            _instance("sensor_1", 5100, 100, "sensor-agent", "/opt/sensor"),
            _instance("sensor_2", 5101, 101, "sensor-agent", "/opt/sensor"),
            _instance("sensor_3", 5102, 102, "sensor-agent", "/opt/sensor"),
            _instance("gateway", 5200, 200, "gateway", "/opt/gateway"),
        ],
    }


@pytest.mark.level_contract
def test_occurrence_expansion_and_reserved_env():
    manifest = to_manifest(load_federation(FIXTURE))
    assert manifest["schema"] == 1
    assert [entry["name"] for entry in manifest["instances"]] == [
        "sensor_1",
        "sensor_2",
        "sensor_3",
        "gateway",
    ]
    assert all(entry["env"] == {} for entry in manifest["instances"])


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


@pytest.mark.level_static
def test_lowering_never_imports_pysos_simulate():
    tree = ast.parse(Path(pysos_sysml.lower.__file__).read_text(encoding="utf-8"))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    assert not [name for name in modules if name.split(".")[0] == "pysos_simulate"]
