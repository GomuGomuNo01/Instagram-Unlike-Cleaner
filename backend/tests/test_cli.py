from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli import app


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0


def test_init_creates_data_dir_and_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_dir))

    result = CliRunner().invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    assert (data_dir / "iuc.db").is_file()
    assert (data_dir / "browser-profile").is_dir()
    assert (data_dir / "logs" / "iuc.log").is_file()
