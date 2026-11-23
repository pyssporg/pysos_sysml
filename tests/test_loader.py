from pathlib import Path

import pytest

from pysos_sysml import SOS_FILE, LaunchDef, SysMLError, load_federation, sos_definitions
from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURES / "federation.sysml"
AIRCRAFT = FIXTURES / "aircraft.sysml"
PRIMARY = FIXTURES / "aircraft_federation.sysml"


def _variant(tmp_path: Path, old: str, new: str) -> Path:
    text = FIXTURE.read_text(encoding="utf-8")
    assert old in text
    path = tmp_path / "bad.sysml"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return path


def _primary_variant(tmp_path: Path, old: str, new: str) -> Path:
    text = PRIMARY.read_text(encoding="utf-8")
    assert old in text
    path = tmp_path / "bad.sysml"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return path


def _assert_error(
    path: Path,
    qualified: str,
    fragment: str,
    *,
    includes: tuple[Path, ...] = (),
) -> None:
    with pytest.raises(SysMLError) as caught:
        load_federation(path, includes=includes)
    assert caught.value.path == path
    message = str(caught.value)
    assert qualified in message
    assert fragment in message


@pytest.mark.level_unit
def test_fixture_loads_to_the_exact_ir():
    assert load_federation(FIXTURE) == FederationDef(
        name="Soc",
        instances=[
            InstanceDef(
                name="sensor",
                part_def="Sensor",
                count=3,
                entities=[
                    EntityDef(site=2, application=7, entity=100, marking="UNCLASSIFIED"),
                    EntityDef(site=2, application=7, entity=101, marking="UNCLASSIFIED"),
                    EntityDef(site=2, application=7, entity=102, marking="UNCLASSIFIED"),
                ],
                telemetry_ports=[
                    EndpointDef(name="telemetry", port=5100),
                    EndpointDef(name="telemetry", port=5101),
                    EndpointDef(name="telemetry", port=5102),
                ],
                control_ports=[
                    EndpointDef(name="control", port=6100),
                    EndpointDef(name="control", port=6101),
                    EndpointDef(name="control", port=6102),
                ],
                command="sensor-agent",
                cwd="/opt/sensor",
            ),
            InstanceDef(
                name="gateway",
                part_def="Gateway",
                count=1,
                entities=[EntityDef(site=1, application=9, entity=200, marking="UNCLASSIFIED")],
                telemetry_ports=[EndpointDef(name="telemetry", port=5200)],
                control_ports=[EndpointDef(name="control", port=6200)],
                command="gateway",
                cwd="/opt/gateway",
            ),
        ],
        metadata={
            "package": "Soc",
            "definition": "Federation",
            "source": "federation.sysml",
        },
    )


@pytest.mark.level_unit
def test_multiplicity_drives_count_and_the_aligned_lists():
    federation = load_federation(FIXTURE)
    sensor, gateway = federation.instances
    assert (sensor.name, sensor.part_def, sensor.count) == ("sensor", "Sensor", 3)
    assert [len(sensor.entities), len(sensor.telemetry_ports), len(sensor.control_ports)] == [
        3,
        3,
        3,
    ]
    assert [entity.entity for entity in sensor.entities] == [100, 101, 102]
    assert [endpoint.port for endpoint in sensor.telemetry_ports] == [5100, 5101, 5102]
    assert [endpoint.port for endpoint in sensor.control_ports] == [6100, 6101, 6102]
    assert (gateway.count, gateway.entities[0].entity) == (1, 200)


@pytest.mark.level_unit
def test_missing_attribute_type_names_the_attribute_path(tmp_path):
    path = _variant(tmp_path, "attribute site : Integer = 2;", "attribute site = 2;")
    _assert_error(path, "Soc::Federation::sensor::site", "no declared type")


@pytest.mark.level_unit
def test_wrong_attribute_type_is_rejected(tmp_path):
    path = _variant(tmp_path, "attribute site : Integer = 2;", "attribute site : Real = 2.0;")
    _assert_error(path, "Soc::Federation::sensor::site", "must be typed Integer")


@pytest.mark.level_unit
def test_missing_required_attribute_is_rejected(tmp_path):
    path = _variant(tmp_path, '      attribute cwd : String = "/opt/sensor";\n', "")
    _assert_error(path, "Soc::Federation::sensor", "missing required attribute 'cwd'")


@pytest.mark.level_unit
def test_optional_scenario_lands_on_the_instance_once_per_usage(tmp_path):
    path = _variant(
        tmp_path,
        '      attribute cwd : String = "/opt/sensor";\n',
        '      attribute cwd : String = "/opt/sensor";\n'
        '      attribute scenario : String = "cruise";\n',
    )
    federation = load_federation(path)
    sensor, gateway = federation.instances
    assert sensor.scenario == "cruise"
    assert sensor.count == 3
    assert [len(sensor.entities), len(sensor.telemetry_ports)] == [3, 3]
    assert gateway.scenario is None


@pytest.mark.level_unit
def test_scenario_is_absent_from_the_ir_when_not_authored():
    sensor, gateway = load_federation(FIXTURE).instances
    assert sensor.scenario is None
    assert gateway.scenario is None


@pytest.mark.level_unit
def test_scenario_must_be_typed_string(tmp_path):
    path = _variant(
        tmp_path,
        '      attribute cwd : String = "/opt/sensor";\n',
        '      attribute cwd : String = "/opt/sensor";\n'
        "      attribute scenario : Integer = 1;\n",
    )
    _assert_error(path, "Soc::Federation::sensor::scenario", "must be typed String")


@pytest.mark.level_unit
def test_scenario_must_be_a_quoted_string_literal(tmp_path):
    path = _variant(
        tmp_path,
        '      attribute cwd : String = "/opt/sensor";\n',
        '      attribute cwd : String = "/opt/sensor";\n'
        "      attribute scenario : String = cruise;\n",
    )
    _assert_error(path, "Soc::Federation::sensor::scenario", "quoted String literal")


@pytest.mark.level_unit
def test_unknown_instance_attribute_is_rejected(tmp_path):
    path = _variant(
        tmp_path,
        "attribute site : Integer = 2;",
        "attribute site : Integer = 2;\n      attribute bogus : Integer = 1;",
    )
    _assert_error(path, "Soc::Federation::sensor::bogus", "outside the supported")


@pytest.mark.level_unit
def test_unknown_part_definition_is_rejected(tmp_path):
    path = _variant(tmp_path, "part sensor : Sensor [3] {", "part sensor : Unknown [3] {")
    _assert_error(path, "Soc::Federation::sensor", "unknown part definition 'Unknown'")


@pytest.mark.level_unit
def test_unknown_top_level_definition_is_rejected(tmp_path):
    path = _variant(
        tmp_path,
        "part def Sensor {",
        "attribute def Extra {\n    attribute x : Integer;\n  }\n\n  part def Sensor {",
    )
    _assert_error(path, "Soc::Extra", "attribute def")


@pytest.mark.level_unit
def test_non_integer_multiplicity_is_rejected(tmp_path):
    path = _variant(tmp_path, "part sensor : Sensor [3] {", "part sensor : Sensor [2..3] {")
    _assert_error(path, "Soc::Federation::sensor[2..3]", "positive integer")


@pytest.mark.level_unit
def test_unparsable_file_raises_sysml_error_with_the_path(tmp_path):
    path = tmp_path / "broken.sysml"
    path.write_text("package Soc {\n  part def Federation {\n", encoding="utf-8")
    with pytest.raises(SysMLError) as caught:
        load_federation(path)
    assert caught.value.path == path
    assert "cannot parse model" in str(caught.value)


@pytest.mark.level_unit
def test_missing_federation_definition_is_rejected(tmp_path):
    path = _variant(tmp_path, "part def Federation {", "part def Setup {")
    _assert_error(path, "Soc::Federation", "missing 'part def Federation'")


@pytest.mark.level_unit
def test_nested_part_inside_an_instance_is_rejected(tmp_path):
    path = _variant(
        tmp_path,
        "attribute site : Integer = 2;",
        "attribute site : Integer = 2;\n      part inner : Sensor;",
    )
    _assert_error(path, "Soc::Federation::sensor::inner", "part inside")


@pytest.mark.level_unit
def test_federation_level_attribute_is_rejected(tmp_path):
    path = _variant(
        tmp_path,
        "part def Federation {",
        'part def Federation {\n    attribute fleet : String = "x";',
    )
    _assert_error(path, "Soc::Federation::fleet", "on Federation")


@pytest.mark.level_unit
def test_bundled_launch_vocabulary_is_real_package_data():
    assert SOS_FILE == "sos.sysml"
    vocabulary = sos_definitions()
    assert vocabulary.is_file()
    assert vocabulary.name == SOS_FILE


@pytest.mark.level_unit
def test_aircraft_and_launch_load_into_the_ir():
    federation = load_federation(PRIMARY, includes=(AIRCRAFT,))
    (jet,) = federation.instances
    assert jet.part_def == "AircraftEntity"
    assert jet.aircraft == "Aircraft::AircraftModel"
    assert jet.launch == LaunchDef(
        mode="supervised",
        readiness="port_bound",
        timeout_s=12.5,
        order=2,
        after_process="supervisor",
    )
    assert jet.scenario == "cruise"
    assert jet.count == 1


@pytest.mark.level_unit
def test_existing_fixture_has_no_aircraft_or_launch():
    sensor, gateway = load_federation(FIXTURE).instances
    assert sensor.aircraft is None and sensor.launch is None
    assert gateway.aircraft is None and gateway.launch is None


@pytest.mark.level_unit
def test_included_root_is_exempt_from_subset_member_checks():
    # aircraft.sysml declares a port def and a specialized, port-bearing decoy.
    federation = load_federation(PRIMARY, includes=(AIRCRAFT,))
    assert federation.instances[0].aircraft == "Aircraft::AircraftModel"


@pytest.mark.level_unit
def test_missing_include_leaves_the_aircraft_type_unknown():
    _assert_error(
        PRIMARY,
        "Flight::AircraftEntity::aircraft",
        "unknown part definition 'AircraftModel'",
    )


@pytest.mark.level_unit
def test_unknown_aircraft_type_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path, "part aircraft : AircraftModel;", "part aircraft : UnknownModel;"
    )
    _assert_error(
        path,
        "Flight::AircraftEntity::aircraft",
        "unknown part definition 'UnknownModel'",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_without_the_vocabulary_import_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path, "  private import PysosSoS::*;\n", ""
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch",
        "unknown part definition 'LaunchSpec'",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_missing_attribute_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        '        attribute readiness : String = "port_bound";\n',
        "",
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch",
        "missing required launch attribute 'readiness'",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_unknown_attribute_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        '        attribute timeout_s : Real = 12.5;\n',
        '        attribute timeout_s : Real = 12.5;\n'
        '        attribute extra : String = "x";\n',
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch::extra",
        "outside the launch vocabulary",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_duplicate_attribute_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        '        attribute readiness : String = "port_bound";\n',
        '        attribute readiness : String = "port_bound";\n'
        '        attribute readiness : String = "log_line";\n',
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch::readiness",
        "duplicate launch attribute",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_wrong_attribute_type_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        "attribute timeout_s : Real = 12.5;",
        "attribute timeout_s : Integer = 12;",
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch::timeout_s",
        "must be typed Real",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_unknown_readiness_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        'attribute readiness : String = "port_bound";',
        'attribute readiness : String = "sometimes";',
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch::readiness",
        "readiness must be one of",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_zero_timeout_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        "attribute timeout_s : Real = 12.5;",
        "attribute timeout_s : Real = 0.0;",
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch::timeout_s",
        "greater than zero",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_negative_order_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        "attribute order : Integer = 2;",
        "attribute order : Integer = -1;",
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch::order",
        "non-negative",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_after_process_must_be_an_identifier(tmp_path):
    path = _primary_variant(
        tmp_path,
        'attribute after_process : String = "supervisor";',
        'attribute after_process : String = "not a name";',
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch::after_process",
        "process/role identifier",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_second_nested_part_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        '        attribute timeout_s : Real = 12.5;\n',
        '        attribute timeout_s : Real = 12.5;\n'
        "      }\n"
        "      part payload : AircraftModel {\n",
    )
    _assert_error(
        path,
        "Flight::Federation::jet::payload",
        "part inside a Federation instance",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_launch_typed_by_a_divergent_definition_is_rejected(tmp_path):
    path = _primary_variant(
        tmp_path,
        "  part def AircraftEntity {",
        "  part def LaunchSpec {\n  }\n\n"
        "  part def AircraftEntity {",
    )
    _assert_error(
        path,
        "Flight::Federation::jet::launch",
        "launch definition must declare exactly",
        includes=(AIRCRAFT,),
    )


@pytest.mark.level_unit
def test_entity_definition_with_a_port_is_rejected(tmp_path):
    path = _variant(
        tmp_path,
        "part def Sensor {\n  }",
        "part def Sensor {\n    in port sig : AircraftSignal;\n  }",
    )
    _assert_error(path, "Soc::Sensor::sig", "port is outside")


@pytest.mark.level_unit
def test_entity_definition_variation_is_rejected(tmp_path):
    path = _variant(tmp_path, "part def Sensor {", "variation part def Sensor {")
    _assert_error(path, "Soc::Sensor", "variation is outside")
