"""Cross-repo proof: the lowered manifest is accepted by pysos_coordinate.

The schema owner is an optional ``[dev]`` dependency. Without it these tests
skip; with it they parse the manifest through the public API and run the
coordinate CLI in validation/port modes, which launch no processes.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pysos_sysml.loader import load_federation
from pysos_sysml.lower import manifest_json

coordinate = pytest.importorskip("pysos_coordinate")

FIXTURES = Path(__file__).parent / "fixtures"
SYSML = FIXTURES / "two_instances.sysml"
MANIFEST = FIXTURES / "two_instances.manifest.json"


@pytest.mark.level_contract
def test_checked_in_manifest_is_the_current_lowering():
    assert manifest_json(load_federation(SYSML)) == MANIFEST.read_text(encoding="utf-8")


@pytest.mark.level_contract
def test_coordinate_parses_the_manifest_without_processes(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(manifest_json(load_federation(SYSML)), encoding="utf-8")

    spec = coordinate.FederationSpec.from_json(json.loads(path.read_text(encoding="utf-8")))
    assert spec.name == "TwoInstances"
    assert [instance.name for instance in spec.instances] == ["alpha", "beta"]
    assert spec.instances[0].command == ["alpha-engine", "--mode", "fast"]
    assert spec.instances[0].entities[0].site == "1"

    # Constructing the supervisor validates the spec; it does not start anything.
    coordinate.Federation(spec)

    for command in ("validate", "ports"):
        result = subprocess.run(
            [sys.executable, "-m", "pysos_coordinate", command, str(path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
