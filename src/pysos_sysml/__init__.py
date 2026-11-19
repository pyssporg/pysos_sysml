"""System-of-systems simulation setup in SysML v2, lowered to a manifest."""

__version__ = "0.2.1"

from pysos_sysml.loader import SysMLError, load_federation
from pysos_sysml.lower import dump_manifest, manifest_json, to_manifest
from pysos_sysml.model import EndpointDef, EntityDef, FederationDef, InstanceDef

__all__ = [
    "EndpointDef",
    "EntityDef",
    "FederationDef",
    "InstanceDef",
    "SysMLError",
    "__version__",
    "dump_manifest",
    "load_federation",
    "manifest_json",
    "to_manifest",
]
