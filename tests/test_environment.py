from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import subprocess
import sys
import tarfile
import tomllib
import unicodedata

import pytest


ROOT = Path(__file__).parents[1]


def test_python_and_uv_pins_match_project_policy() -> None:
    environment = (ROOT / "environment.yml").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "  - python=3.12.14\n" in environment
    assert "  - uv=0.12.9\n" in environment
    assert "  - streamlit=1.49.1\n" in environment
    assert "  - plotly=6.3.0\n" in environment
    assert "  - pip=" not in environment
    assert "  - pip:\n" not in environment
    assert project["project"]["requires-python"] == ">=3.12,<3.13"
    assert project["tool"]["uv"]["managed"] is False
    assert sys.version_info[:2] == (3, 12)


def test_setuptools_security_pin_matches_build_environment() -> None:
    environment = (ROOT / "environment.yml").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert "  - setuptools=83.0.0\n" in environment
    assert project["build-system"]["requires"] == ["setuptools==83.0.0"]
    assert version("setuptools") == "83.0.0"


@pytest.mark.parametrize(
    "file_form,rule_form", [("NFD", "NFC"), ("NFC", "NFD"), ("NFC", "NFC")],
)
@pytest.mark.parametrize(
    "rule,target",
    [
        ("exclude secret_café.txt", "secret_café.txt"),
        ("global-exclude secret_café.txt", "nested/secret_café.txt"),
        ("recursive-exclude café *.txt", "café/secret.txt"),
        ("prune café", "café/secret.txt"),
    ],
)
def test_sdist_exclusions_handle_unicode_normalization(
    file_form: str, rule_form: str, rule: str, target: str,
) -> None:
    """GHSA-h35f-9h28-mq5c: exclusions must not leak equivalent Unicode paths."""
    from setuptools.command.egg_info import FileList

    files = FileList()
    # Exercise the manifest boundary without relying on host filesystem spelling.
    files.files = [
        unicodedata.normalize(file_form, target), "public.txt", "secret_ascii.txt",
    ]
    files.process_template_line(unicodedata.normalize(rule_form, rule))
    files.process_template_line("global-exclude secret_ascii.txt")
    assert files.files == ["public.txt"]


def test_sdist_archive_does_not_publish_excluded_unicode_file(tmp_path: Path) -> None:
    """Verify the configured backend, not only its manifest matching helper."""
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["setuptools==83.0.0"]\n'
        'build-backend = "setuptools.build_meta"\n'
        '[project]\nname = "manifest-security-control"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "control.py").write_text('"""Harmless package control."""\n', encoding="utf-8")
    (tmp_path / "public.txt").write_text("public control", encoding="utf-8")
    (tmp_path / unicodedata.normalize("NFD", "secret_café.txt")).write_text(
        "synthetic test data, not a real secret", encoding="utf-8",
    )
    (tmp_path / "MANIFEST.in").write_text(
        "global-include *.txt\nglobal-exclude secret_café.txt\n", encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, "-c", "from setuptools.build_meta import build_sdist; build_sdist('dist')"],
        cwd=tmp_path, check=True, capture_output=True, text=True, timeout=60,
    )
    archives = list((tmp_path / "dist").glob("*.tar.gz"))
    assert len(archives) == 1
    with tarfile.open(archives[0]) as archive:
        names = [unicodedata.normalize("NFC", name) for name in archive.getnames()]
    assert any(name.endswith("/public.txt") for name in names)
    assert any(name.endswith("/control.py") for name in names)
    assert not any(name.endswith("/secret_café.txt") for name in names)
