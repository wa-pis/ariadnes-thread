from __future__ import annotations

from pathlib import Path
import sys
import tomllib


ROOT = Path(__file__).parents[1]


def test_python_and_uv_pins_match_project_policy() -> None:
    environment = (ROOT / "environment.yml").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "  - python=3.12.14\n" in environment
    assert "  - uv=0.12.9\n" in environment
    assert "  - pip=" not in environment
    assert "  - pip:\n" not in environment
    assert project["project"]["requires-python"] == ">=3.12,<3.13"
    assert project["tool"]["uv"]["managed"] is False
    assert sys.version_info[:2] == (3, 12)
