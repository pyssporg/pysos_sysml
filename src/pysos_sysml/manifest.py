"""Render a setup file's manifest and compare it with a checked-in copy."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pysos_sysml.loader import load_federation
from pysos_sysml.lower import manifest_json

__all__ = ["check", "render"]


def render(path: Path | str, *, includes: Sequence[Path | str] = ()) -> str:
    """Return the current schema-1 lowering of the setup at *path*."""
    return manifest_json(load_federation(path, includes=includes))


def check(
    path: Path | str,
    expected_path: Path | str,
    *,
    includes: Sequence[Path | str] = (),
) -> bool:
    """Return whether *expected_path* is byte-identical to :func:`render`.

    A missing *expected_path* is not an error: it is simply not current.
    """
    actual = render(path, includes=includes).encode("utf-8")
    try:
        expected = Path(expected_path).read_bytes()
    except FileNotFoundError:
        return False
    return expected == actual
