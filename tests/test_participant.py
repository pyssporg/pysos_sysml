"""The promoted entity plane: variants, named sets, apps, participant wrappers.

The model text mirrors the frozen ``AircraftFederation`` contract in a small
form: four aviation variants, one named scenario/identity/transport set each,
four application wrappers, four participant wrappers and a bare-usage
``Federation``. ``Aircraft`` is a local fixture; ``PysspCore`` is loaded from the
shared vocabulary root so the test cannot drift from the shipped roles.
"""

from pathlib import Path

import pytest
from pycps_sysml2 import core_definitions

from pysos_sysml import LaunchDef, SysMLError, load_federation
from pysos_sysml.lower import to_manifest
from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef

AIRCRAFT = """package Aircraft {
  private import PysspCore::*;

  part def AircraftModel {
  }

  attribute def BaselineExperiment :> Experiment {
    attribute startTime : Real = 0.0;
    attribute stopTime : Real = 120.0;
    attribute stepSize : Real = 0.1;
  }
}
"""

LOOKALIKE = """package Lookalike {
  attribute def ParameterSet;
}
"""

_VARIANTS = (
    ("RedInterceptor", "RED-1", 1, 5510),
    ("RedStriker", "RED-2", 2, 5512),
    ("BlueCas", "BLUE-1", 3, 5514),
    ("BlueBaseline", "BLUE-2", 4, 5516),
)


def _model_text() -> str:
    lines = [
        "package AircraftFederation {",
        "  private import Aircraft::*;",
        "  private import PysosSoS::*;",
        "  private import PysspCore::*;",
        "",
        "  port def RprBroadcast;",
        "  port def RprListener;",
        "",
        "  part def AircraftVariant :> AircraftModel;",
        "",
    ]
    for name, _marking, _entity, port in _VARIANTS:
        lines += [
            f"  attribute def {name}Scenario :> ParameterSet {{",
            "    attribute initX_km : Real = 0.0;",
            "    attribute targetAirspeed_mps : Real = 500.0;",
            "    attribute waypointX_km : Real[2] = (1.0, 2.0);",
            "  }",
            f"  attribute def {name}Identity :> ParameterSet {{",
            "    attribute reference_latitude_deg : Real = -2.957519;",
            "    attribute reference_longitude_deg : Real = 39.232955;",
            "    attribute reference_altitude_m : Real = 0.0;",
            "    attribute entity_site : Integer = 1;",
            "    attribute entity_application : Integer = 2;",
            f"    attribute entity_entity : Integer = {_entity};",
            f'    attribute marking_characters : String = "{_marking}";',
            "  }",
            f"  attribute def {name}Transport :> ParameterSet {{",
            '    attribute transport : String = "udp";',
            f'    attribute bind_address : String = "127.0.0.1:{port}";',
            '    attribute peer_address : String = "127.0.0.1:5505";',
            "  }",
            f"  part def {name} :> AircraftVariant {{",
            "    attribute experiment : BaselineExperiment;",
            f"    attribute scenario : {name}Scenario;",
            f"    attribute identity : {name}Identity;",
            f"    attribute transport : {name}Transport;",
            "    bind environment.parameters.initX_km = scenario.initX_km;",
            "  }",
        ]
    lines += [
        "  part def AircraftApplication :> Application {",
        "    attribute participant : String;",
        '    attribute roles : String = "aircraft";',
        "    attribute command : String;",
        '    attribute cwd : String = ".";',
        '    attribute waypointFrame : String = "federation";',
        "    part launch : LaunchSpec;",
        "  }",
    ]
    for name, _marking, _entity, _port in _VARIANTS:
        lines += [
            f"  part def {name}App :> AircraftApplication {{",
            f'    attribute participant : String = "{name}";',
            f'    attribute command : String = "run --variant {name}";',
            "    part launch : LaunchSpec {",
            '      attribute mode : String = "supervised";',
            '      attribute readiness : String = "port_bound";',
            "      attribute timeout_s : Real = 30.0;",
            "      attribute order : Integer = 2;",
            '      attribute after_process : String = "supervisor";',
            "    }",
            "  }",
            f"  part def {name}Participant {{",
            f"    part aircraft : {name};",
            f"    part application : {name}App;",
            "    port telemetry : RprBroadcast;",
            "  }",
        ]
    lines += ["  part def Federation {"]
    for name, _marking, _entity, _port in _VARIANTS:
        usage = _usage_name(name)
        lines.append(f"    part {usage} : {name}Participant;")
    lines += ["  }", "}", ""]
    return "\n".join(lines)


def _usage_name(variant: str) -> str:
    return {
        "RedInterceptor": "red_interceptor",
        "RedStriker": "red_striker",
        "BlueCas": "blue_cas",
        "BlueBaseline": "blue_baseline",
    }[variant]


def _write_model(tmp_path: Path) -> Path:
    aircraft = tmp_path / "aircraft.sysml"
    aircraft.write_text(AIRCRAFT, encoding="utf-8")
    primary = tmp_path / "aircraft_federation.sysml"
    primary.write_text(_model_text(), encoding="utf-8")
    return primary


def _load(tmp_path: Path) -> FederationDef:
    return load_federation(
        _write_model(tmp_path),
        includes=(tmp_path / "aircraft.sysml", core_definitions()),
    )


def _variant_path(tmp_path: Path, old: str, new: str) -> Path:
    path = _write_model(tmp_path)
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return path


@pytest.mark.level_unit
def test_local_markers_and_parameter_sets_are_accepted(tmp_path):
    federation = _load(tmp_path)
    assert [instance.name for instance in federation.instances] == [
        "red_interceptor",
        "red_striker",
        "blue_cas",
        "blue_baseline",
    ]
    assert {instance.part_def for instance in federation.instances} == {
        "RedInterceptorParticipant",
        "RedStrikerParticipant",
        "BlueCasParticipant",
        "BlueBaselineParticipant",
    }


@pytest.mark.level_unit
def test_derived_parameter_set_chain_is_accepted(tmp_path):
    path = _write_model(tmp_path)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "  attribute def RedInterceptorScenario :> ParameterSet {",
        "  attribute def RedScenarioBase :> ParameterSet {\n"
        "    attribute shared : Real = 1.0;\n"
        "  }\n"
        "  attribute def RedInterceptorScenario :> RedScenarioBase {",
        1,
    )
    path.write_text(text, encoding="utf-8")
    federation = load_federation(
        path, includes=(tmp_path / "aircraft.sysml", core_definitions())
    )
    red = next(
        instance
        for instance in federation.instances
        if instance.name == "red_interceptor"
    )
    assert red.scenario_values["shared"] == 1.0
    assert red.scenario_values["initX_km"] == 0.0


@pytest.mark.level_unit
def test_attribute_definition_must_specialize_parameter_set(tmp_path):
    """A parameter set is recognized by its supertype, never by its name."""
    path = _variant_path(
        tmp_path,
        "  attribute def RedInterceptorScenario :> ParameterSet {",
        "  attribute def RedInterceptorScenario {",
    )
    with pytest.raises(SysMLError) as caught:
        load_federation(
            path,
            includes=(tmp_path / "aircraft.sysml", core_definitions()),
        )
    assert "specializes ParameterSet" in str(caught.value)


@pytest.mark.level_unit
def test_parameter_set_marker_must_be_the_included_core_definition(tmp_path):
    """A lookalike definition only shares the name; identity decides."""
    path = _write_model(tmp_path)
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "  private import PysspCore::*;",
        "  private import PysspCore::*;\n  private import Lookalike::*;",
        1,
    ).replace(
        "  attribute def RedInterceptorScenario :> ParameterSet {",
        "  attribute def RedInterceptorScenario :> Lookalike::ParameterSet {",
        1,
    )
    path.write_text(text, encoding="utf-8")
    (tmp_path / "lookalike.sysml").write_text(LOOKALIKE, encoding="utf-8")

    with pytest.raises(SysMLError) as caught:
        load_federation(
            path,
            includes=(
                tmp_path / "aircraft.sysml",
                tmp_path / "lookalike.sysml",
                core_definitions(),
            ),
        )
    assert "RedInterceptorScenario" in str(caught.value)
    assert "specializes ParameterSet" in str(caught.value)


@pytest.mark.level_unit
def test_parameter_set_requires_the_shared_core_root(tmp_path):
    path = _write_model(tmp_path)
    with pytest.raises(SysMLError) as caught:
        load_federation(path, includes=(tmp_path / "aircraft.sysml",))
    message = str(caught.value)
    assert "PysspCore::ParameterSet" in message
    assert str(core_definitions()) in message


@pytest.mark.level_unit
def test_variant_root_resolves_to_the_imported_aircraft_model(tmp_path):
    federation = _load(tmp_path)
    assert {instance.aircraft for instance in federation.instances} == {
        "Aircraft::AircraftModel"
    }


@pytest.mark.level_unit
def test_identity_transport_and_application_are_resolved(tmp_path):
    by_name = {instance.name: instance for instance in _load(tmp_path).instances}
    red = by_name["red_interceptor"]
    assert red.entities == [
        EntityDef(site=1, application=2, entity=1, marking="RED-1")
    ]
    assert red.telemetry_ports == [
        EndpointDef(name="telemetry", port=5510, host="127.0.0.1")
    ]
    assert red.control_ports == []
    assert red.command == "run --variant RedInterceptor"
    assert red.cwd == "."
    assert red.launch == LaunchDef(
        mode="supervised",
        readiness="port_bound",
        timeout_s=30.0,
        order=2,
        after_process="supervisor",
    )
    assert dict(red.scenario_values) == {
        "initX_km": 0.0,
        "targetAirspeed_mps": 500.0,
        "waypointX_km": (1.0, 2.0),
    }
    assert by_name["blue_baseline"].entities == [
        EntityDef(site=1, application=2, entity=4, marking="BLUE-2")
    ]


@pytest.mark.level_unit
def test_owner_values_are_exposed_as_read_only_mappings(tmp_path):
    red = next(
        instance
        for instance in _load(tmp_path).instances
        if instance.name == "red_interceptor"
    )
    assert dict(red.identity_values) == {
        "reference_latitude_deg": -2.957519,
        "reference_longitude_deg": 39.232955,
        "reference_altitude_m": 0.0,
        "entity_site": 1,
        "entity_application": 2,
        "entity_entity": 1,
        "marking_characters": "RED-1",
    }
    assert dict(red.transport_values) == {
        "transport": "udp",
        "bind_address": "127.0.0.1:5510",
        "peer_address": "127.0.0.1:5505",
    }
    assert dict(red.application_values) == {
        "participant": "RedInterceptor",
        "roles": "aircraft",
        "command": "run --variant RedInterceptor",
        "cwd": ".",
        "waypointFrame": "federation",
    }
    assert dict(red.experiment_values) == {
        "startTime": 0.0,
        "stopTime": 120.0,
        "stepSize": 0.1,
    }
    assert red.waypoint_frame == "federation"


@pytest.mark.level_unit
def test_manifest_has_one_telemetry_endpoint_and_no_control_or_scenario(tmp_path):
    manifest = to_manifest(_load(tmp_path))
    assert manifest["schema"] == 1
    assert len(manifest["instances"]) == 4
    for entry in manifest["instances"]:
        assert len(entry["telemetry"]) == 1
        assert "control" not in entry
        assert "PYSOS_CONTROL_PORT" not in entry["env"]
        assert "PYSOS_SCENARIO" not in entry["env"]
        assert entry["env"]["PYSOS_TELEMETRY_PORT"] == str(
            entry["telemetry"][0]["port"]
        )
        assert entry["env"]["PYSOS_LAUNCH_MODE"] == "supervised"


@pytest.mark.level_unit
def test_marker_port_definition_with_attributes_is_rejected(tmp_path):
    path = _variant_path(
        tmp_path,
        "  port def RprBroadcast;",
        "  port def RprBroadcast {\n    attribute gain : Real;\n  }",
    )
    with pytest.raises(SysMLError) as caught:
        load_federation(
            path,
            includes=(tmp_path / "aircraft.sysml", core_definitions()),
        )
    assert "port def is outside" in str(caught.value)


@pytest.mark.level_unit
def test_transport_must_be_udp(tmp_path):
    path = _variant_path(
        tmp_path,
        'attribute transport : String = "udp";',
        'attribute transport : String = "tcp";',
    )
    with pytest.raises(SysMLError) as caught:
        load_federation(
            path,
            includes=(tmp_path / "aircraft.sysml", core_definitions()),
        )
    assert "transport must be 'udp'" in str(caught.value)


@pytest.mark.level_unit
def test_bind_address_must_be_host_and_port(tmp_path):
    path = _variant_path(
        tmp_path,
        'attribute bind_address : String = "127.0.0.1:5510";',
        'attribute bind_address : String = "127.0.0.1";',
    )
    with pytest.raises(SysMLError) as caught:
        load_federation(
            path,
            includes=(tmp_path / "aircraft.sysml", core_definitions()),
        )
    assert "bind_address must be 'host:port'" in str(caught.value)


@pytest.mark.level_unit
def test_application_launch_body_is_validated_as_before(tmp_path):
    path = _variant_path(
        tmp_path,
        '      attribute readiness : String = "port_bound";\n',
        "",
    )
    with pytest.raises(SysMLError) as caught:
        load_federation(
            path,
            includes=(tmp_path / "aircraft.sysml", core_definitions()),
        )
    assert "missing required launch attribute 'readiness'" in str(caught.value)


@pytest.mark.level_unit
def test_instance_without_control_ports_lowers_without_control(tmp_path):
    instance = InstanceDef(
        name="node",
        part_def="Node",
        count=1,
        entities=[EntityDef(site=1, application=2, entity=3, marking="U")],
        telemetry_ports=[EndpointDef(name="telemetry", port=5510)],
        control_ports=[],
        command="run",
        cwd="/",
    )
    entry = to_manifest(FederationDef(name="Soc", instances=[instance]))["instances"][0]
    assert "control" not in entry
    assert entry["env"] == {"PYSOS_TELEMETRY_PORT": "5510"}
