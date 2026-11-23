from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef, LaunchDef


def test_endpoint_defaults_to_loopback_and_keeps_an_explicit_host():
    assert EndpointDef(name="telemetry", port=5100) == EndpointDef(
        name="telemetry", port=5100, host="127.0.0.1"
    )
    assert EndpointDef(name="control", port=6100, host="0.0.0.0").host == "0.0.0.0"


def test_ir_is_plain_dataclasses_with_the_declared_field_order():
    entity = EntityDef(site=1, application=2, entity=3, marking="UNCLASSIFIED")
    instance = InstanceDef(
        name="node",
        part_def="Node",
        count=1,
        entities=[entity],
        telemetry_ports=[EndpointDef(name="telemetry", port=5000)],
        control_ports=[EndpointDef(name="control", port=6000)],
        command="run-node",
        cwd="/opt/node",
    )
    federation = FederationDef(name="Soc", instances=[instance])
    assert federation.metadata == {}
    assert federation.instances[0].entities == [entity]
    assert (instance.count, instance.part_def) == (1, "Node")


def test_launch_and_aircraft_default_to_none_and_keep_their_values():
    instance = InstanceDef(
        name="node",
        part_def="Node",
        count=1,
        entities=[],
        telemetry_ports=[],
        control_ports=[],
        command="run",
        cwd="/",
    )
    assert instance.launch is None and instance.aircraft is None
    launch = LaunchDef(
        mode="operator",
        readiness="log_line",
        timeout_s=5.0,
        order=0,
        after_process="builder",
    )
    assert launch.mode == "operator"
    assert launch.readiness == "log_line"
    assert launch.timeout_s == 5.0
    assert launch.order == 0
    assert launch.after_process == "builder"
