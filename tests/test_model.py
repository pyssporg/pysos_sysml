from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef


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
