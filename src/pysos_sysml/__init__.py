"""System-of-systems simulation setup in SysML v2, lowered to a manifest."""

__version__ = "0.4.0"

from pysos_sysml.loader import SOS_FILE, SysMLError, load_federation, sos_definitions
from pysos_sysml.lower import dump_manifest, manifest_json, to_manifest
from pysos_sysml.manifest import check, render
from pysos_sysml.model import (
    EndpointDef,
    EntityDef,
    FederationDef,
    InstanceDef,
    LaunchDef,
)

__all__ = [
    "SOS_FILE",
    "EndpointDef",
    "EntityDef",
    "FederationDef",
    "InstanceDef",
    "LaunchDef",
    "SysMLError",
    "__version__",
    "check",
    "dump_manifest",
    "load_federation",
    "manifest_json",
    "render",
    "sos_definitions",
    "to_manifest",
]
