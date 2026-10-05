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


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--start", "2099-01-01"], "futur"),
        (["--start", "2025-06-01", "--end", "2025-01-01"], "précéder"),
        (["--author", "deux mots"], "nom de compte"),
        (["--author", "auteur", "--exclude-author", "@auteur"], "inclus et exclu"),
    ],
)
def test_preview_rejects_invalid_criteria_before_opening_the_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arguments: list[str], message: str
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    result = CliRunner().invoke(app, ["preview", *arguments])

    assert result.exit_code == 2
    assert message in result.output
    assert not (tmp_path / "data").exists()  # ni base, ni navigateur
