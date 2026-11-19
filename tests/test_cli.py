import json
from pathlib import Path

import pytest

from pysos_sysml.cli import main
from pysos_sysml.loader import load_federation
from pysos_sysml.lower import manifest_json, to_manifest

FIXTURE = Path(__file__).parent / "fixtures" / "federation.sysml"


@pytest.mark.level_system
def test_validate_prints_the_counts(capsys):
    assert main(["validate", str(FIXTURE)]) == 0
    output = capsys.readouterr().out.splitlines()
    assert output == [
        "federation: Soc",
        "instances: 2",
        "occurrences: 4",
        "entities: 4",
        "telemetry endpoints: 4",
        "control endpoints: 4",
    ]


@pytest.mark.level_system
def test_manifest_writes_json_to_stdout(capsys):
    assert main(["manifest", str(FIXTURE)]) == 0
    assert json.loads(capsys.readouterr().out) == to_manifest(load_federation(FIXTURE))


@pytest.mark.level_system
def test_manifest_output_file_is_byte_identical_to_the_library(tmp_path):
    target = tmp_path / "manifest.json"
    assert main(["manifest", str(FIXTURE), "-o", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == manifest_json(load_federation(FIXTURE))


@pytest.mark.level_system
def test_invalid_input_exits_two_and_names_the_offender(tmp_path, capsys):
    text = FIXTURE.read_text(encoding="utf-8")
    path = tmp_path / "bad.sysml"
    path.write_text(
        text.replace("attribute site : Integer = 2;", "attribute site = 2;", 1),
        encoding="utf-8",
    )
    assert main(["validate", str(path)]) == 2
    stderr = capsys.readouterr().err
    assert str(path) in stderr
    assert "Soc::Federation::sensor::site" in stderr
