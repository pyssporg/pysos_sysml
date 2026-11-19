import json
from pathlib import Path

import pytest

from pysos_sysml.cli import MAX_DIFF_LINES, main
from pysos_sysml.loader import load_federation
from pysos_sysml.lower import manifest_json, to_manifest
from pysos_sysml.manifest import check, render

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE = FIXTURES / "federation.sysml"


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


@pytest.mark.level_component
def test_render_and_check_share_the_manifest_formatting(tmp_path):
    text = render(FIXTURE)
    assert text == manifest_json(load_federation(FIXTURE))
    target = tmp_path / "manifest.json"
    target.write_text(text, encoding="utf-8")
    assert check(FIXTURE, target)
    assert not check(FIXTURE, tmp_path / "absent.json")
    target.write_text(text + "\n", encoding="utf-8")
    assert not check(FIXTURE, target)


@pytest.mark.level_system
def test_manifest_check_accepts_the_checked_in_fixture(capsys):
    sysml = FIXTURES / "two_instances.sysml"
    expected = FIXTURES / "two_instances.manifest.json"
    assert main(["manifest", str(sysml), "-o", str(expected), "--check"]) == 0
    assert capsys.readouterr().out == f"ok: {expected} is up to date\n"


@pytest.mark.level_system
def test_manifest_check_detects_stale_content_with_a_bounded_diff(tmp_path, capsys):
    target = tmp_path / "manifest.json"
    target.write_text("stale\n", encoding="utf-8")
    assert main(["manifest", str(FIXTURE), "-o", str(target), "--check"]) == 1
    stderr = capsys.readouterr().err
    assert "is not up to date" in stderr
    assert "--- " in stderr and "+++ lowered" in stderr
    assert len(stderr.splitlines()) <= MAX_DIFF_LINES + 2
    assert target.read_text(encoding="utf-8") == "stale\n"


@pytest.mark.level_system
def test_manifest_check_missing_expected_file_is_drift(tmp_path, capsys):
    target = tmp_path / "absent.json"
    assert main(["manifest", str(FIXTURE), "-o", str(target), "--check"]) == 1
    assert "is missing" in capsys.readouterr().err
    assert not target.exists()


@pytest.mark.level_system
def test_manifest_check_without_output_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["manifest", str(FIXTURE), "--check"])
    assert excinfo.value.code == 2
    assert "--check requires -o/--output" in capsys.readouterr().err
