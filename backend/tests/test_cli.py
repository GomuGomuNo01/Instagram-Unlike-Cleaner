from datetime import date
from pathlib import Path

import pytest
from sqlmodel import Session
from typer.testing import CliRunner

from app.cli import app
from app.core.db import init_db, make_engine
from app.models.schemas import CleanupFilters
from app.models.tables import Job, JobStatus, LikedItem, MediaKind


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
        # Seul le filtre d'Instagram existe : plus de type de contenu ni de comptes.
        (["--content", "reels"], "No such option"),
        (["--exclude-author", "auteur"], "No such option"),
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


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    return data_dir


def make_ready_job(data_dir: Path, authors: list[str]) -> int:
    """Nettoyage prêt, enregistré directement dans la base du dossier de données."""
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = make_engine(data_dir / "iuc.db")
    init_db(engine)
    with Session(engine) as db:
        job = Job(filters=CleanupFilters().model_dump(mode="json"), status=JobStatus.READY)
        db.add(job)
        db.flush()
        assert job.id is not None
        for position, author in enumerate(authors):
            db.add(
                LikedItem(
                    job_id=job.id,
                    media_key=f"{position}_1_1_n",
                    position=position,
                    label="libellé",
                    author=author,
                    media_kind=MediaKind.VIDEO,
                    published_on=date(2026, 10, 3),
                )
            )
        db.commit()
        job_id = job.id
    engine.dispose()
    return job_id


def test_jobs_lists_nothing_at_first(data_dir: Path) -> None:
    result = CliRunner().invoke(app, ["jobs"])

    assert result.exit_code == 0
    assert "Aucun nettoyage" in result.output


def test_jobs_and_exclude(data_dir: Path) -> None:
    job_id = make_ready_job(data_dir, ["a", "b", "a"])

    excluded = CliRunner().invoke(app, ["exclude", str(job_id), "--author", "@a"])
    listed = CliRunner().invoke(app, ["jobs"])

    assert excluded.exit_code == 0, excluded.output
    assert "2 likes exclus" in excluded.output
    assert f"n°{job_id} [prêt]" in listed.output
    assert "à traiter 1" in listed.output
    assert "exclus 2" in listed.output


def test_exclude_needs_a_target(data_dir: Path) -> None:
    result = CliRunner().invoke(app, ["exclude", "1"])

    assert result.exit_code == 2


def test_run_refuses_unknown_job_before_opening_the_browser(data_dir: Path) -> None:
    result = CliRunner().invoke(app, ["run", "7"])

    assert result.exit_code == 1
    assert "inexistant" in result.output
    assert not (data_dir / "browser-profile" / "Default").exists()


def test_run_asks_for_confirmation(data_dir: Path) -> None:
    job_id = make_ready_job(data_dir, ["a", "b"])

    result = CliRunner().invoke(app, ["run", str(job_id), "--limit", "1"], input="n\n")

    assert result.exit_code == 1
    assert "Retirer jusqu'à 1 likes maintenant" in result.output
    assert "Rien n'a été retiré." in result.output
    assert not (data_dir / "browser-profile" / "Default").exists()


def test_report_command_writes_csv_and_json(data_dir: Path) -> None:
    job_id = make_ready_job(data_dir, ["a", "b"])

    result = CliRunner().invoke(app, ["report", str(job_id)])

    assert result.exit_code == 0, result.output
    assert f"Nettoyage n°{job_id} : prêt" in result.output
    assert "Likes ciblés : 2" in result.output
    assert (data_dir / "reports" / f"rapport-{job_id}.csv").is_file()
    assert (data_dir / "reports" / f"rapport-{job_id}.json").is_file()


def test_report_of_unknown_job(data_dir: Path) -> None:
    result = CliRunner().invoke(app, ["report", "404"])

    assert result.exit_code == 1
    assert "Aucun nettoyage n°404" in result.output


def test_stop_then_run_is_refused(data_dir: Path) -> None:
    job_id = make_ready_job(data_dir, ["a"])

    stopped = CliRunner().invoke(app, ["stop", str(job_id), "--yes"])
    relaunched = CliRunner().invoke(app, ["run", str(job_id), "--yes"])

    assert stopped.exit_code == 0, stopped.output
    assert f"Nettoyage n°{job_id} arrêté." in stopped.output
    assert relaunched.exit_code == 1
    assert "« arrêté »" in relaunched.output


def test_stop_asks_for_confirmation(data_dir: Path) -> None:
    job_id = make_ready_job(data_dir, ["a"])

    result = CliRunner().invoke(app, ["stop", str(job_id)], input="n\n")
    listed = CliRunner().invoke(app, ["jobs"])

    assert result.exit_code == 1
    assert f"n°{job_id} [prêt]" in listed.output


def test_logout_deletes_only_the_browser_profile(data_dir: Path) -> None:
    job_id = make_ready_job(data_dir, ["a"])
    (data_dir / "browser-profile" / "Default").mkdir(parents=True)

    first = CliRunner().invoke(app, ["logout", "--yes"])
    second = CliRunner().invoke(app, ["logout", "--yes"])

    assert "IUC n'est plus connecté à Instagram" in first.output
    assert "Aucun profil de navigateur" in second.output
    assert not (data_dir / "browser-profile").exists()
    assert CliRunner().invoke(app, ["report", str(job_id)]).exit_code == 0  # base conservée


def test_purge_deletes_all_local_data(data_dir: Path) -> None:
    make_ready_job(data_dir, ["a"])

    result = CliRunner().invoke(app, ["purge", "--yes"])

    assert result.exit_code == 0, result.output
    assert "Supprimé" in result.output
    assert not (data_dir / "iuc.db").exists()
    assert data_dir.is_dir()


def test_purge_refuses_a_folder_with_other_files_before_asking(data_dir: Path) -> None:
    make_ready_job(data_dir, ["a"])
    (data_dir / "Mes documents").mkdir()

    result = CliRunner().invoke(app, ["purge"])

    assert result.exit_code == 1
    assert "Mes documents" in result.output
    assert "Supprimer définitivement" not in result.output
    assert (data_dir / "iuc.db").exists()


def test_version_is_the_single_package_version() -> None:
    from importlib.metadata import version

    from app import __version__

    result = CliRunner().invoke(app, ["version"])

    assert result.output.strip() == __version__ == version("iuc")
