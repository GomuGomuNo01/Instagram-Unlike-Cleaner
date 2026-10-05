"""Démonstration de l'interface avec des données entièrement fictives, sans compte Instagram.

    python scripts/demo.py

Crée le dossier `demo-data/` (recréé à chaque lancement, jamais celui de tes vraies données)
avec trois nettoyages fictifs (terminé, en pause, prêt), puis sert l'interface compilée sur
http://127.0.0.1:8799. Sert aux captures d'écran du README et à découvrir l'interface.
Instagram n'est contacté que si tu cliques toi-même sur « Ouvrir Instagram ».
"""

import random
import shutil
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.core.db import init_db, make_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.schemas import CleanupFilters  # noqa: E402
from app.models.tables import (  # noqa: E402
    DailyCounter,
    EventLog,
    ItemStatus,
    Job,
    JobStatus,
    LikedItem,
    MediaKind,
)
from app.services.cleanup import RUN_STARTED_EVENT, STOP_MESSAGES, StopReason  # noqa: E402
from app.services.report import write_report_files  # noqa: E402

DEMO_DIR = ROOT / "demo-data"
PORT = 8799
ACCOUNT = "1000000001"  # identifiant fictif

# Comptes fictifs, pondérés : les premiers ont été « aimés » bien plus souvent.
AUTHORS = [
    "compte_humour",
    "page_memes",
    "club_sport",
    "cuisine_facile",
    "voyage_photo",
    "musique_live",
    "atelier_design",
    "cine_club",
    "jardin_urbain",
    "velo_passion",
    "recettes_maison",
    "galerie_art",
    "astuces_tech",
    "rando_alpes",
    "chats_droles",
    "ami_proche",
]
KINDS = [(MediaKind.VIDEO, "Vidéo"), (MediaKind.PHOTO, "Photo"), (MediaKind.CAROUSEL, "Carrousel")]
ERRORS = {
    ItemStatus.FAILED: "réapparu après rechargement : Instagram n'a pas retiré ce like",
    ItemStatus.SKIPPED: "introuvable dans la grille",
}
MONTHS = "January February March April May June July August September October November December"


def published_label(day: date) -> str:
    return f"{MONTHS.split()[day.month - 1]} {day.day}, {day.year}"


def add_job(
    db: Session,
    rng: random.Random,
    *,
    filters: CleanupFilters,
    status: JobStatus,
    targeted: int,
    created: datetime,
    outcome: dict[ItemStatus, int],
) -> Job:
    job = Job(
        filters=filters.model_dump(mode="json"),
        status=status,
        account_id=ACCOUNT,
        created_at=created,
    )
    db.add(job)
    db.flush()
    assert job.id is not None
    statuses = [state for state, count in outcome.items() for _ in range(count)]
    statuses += [ItemStatus.PENDING if status is JobStatus.READY else ItemStatus.SELECTED] * (
        targeted - len(statuses)
    )
    weights = [len(AUTHORS) - index for index in range(len(AUTHORS))]
    for position, state in enumerate(statuses):
        kind, kind_text = rng.choice(KINDS)
        author = rng.choices(AUTHORS, weights)[0]
        published = date(2021, 1, 1) + timedelta(days=rng.randrange(0, 1500))
        label = f"{kind_text}, {position % 18 + 1} sur 18, de @{author}, partagée le " + (
            published_label(published)
        )
        processed = (
            created + timedelta(minutes=10 + position // 18)
            if state
            in (
                ItemStatus.DONE,
                ItemStatus.FAILED,
                ItemStatus.SKIPPED,
            )
            else None
        )
        db.add(
            LikedItem(
                job_id=job.id,
                media_key=f"{9000 + job.id}{position:05d}_{rng.randrange(10**15)}_{position}_n",
                position=position,
                label=label,
                author=author,
                media_kind=kind,
                published_on=published,
                status=state,
                error=ERRORS.get(state),
                processed_at=processed,
            )
        )
    return job


def seed(settings: Settings) -> None:
    rng = random.Random(2026)
    now = datetime.now(UTC).replace(microsecond=0)
    engine = make_engine(settings.db_path)
    init_db(engine)
    with Session(engine) as db:
        done = add_job(
            db,
            rng,
            filters=CleanupFilters(start_date=date(2021, 1, 1), end_date=date(2022, 12, 31)),
            status=JobStatus.COMPLETED,
            targeted=126,
            created=now - timedelta(days=2, hours=3),
            outcome={
                ItemStatus.DONE: 117,
                ItemStatus.EXCLUDED: 6,
                ItemStatus.FAILED: 2,
                ItemStatus.SKIPPED: 1,
            },
        )
        paused = add_job(
            db,
            rng,
            filters=CleanupFilters(content="reels", exclude_authors=["ami_proche"]),
            status=JobStatus.PAUSED,
            targeted=342,
            created=now - timedelta(hours=5),
            outcome={ItemStatus.DONE: 150, ItemStatus.EXCLUDED: 12},
        )
        add_job(
            db,
            rng,
            filters=CleanupFilters(include_authors=["page_memes", "compte_humour"]),
            status=JobStatus.READY,
            targeted=64,
            created=now - timedelta(minutes=20),
            outcome={ItemStatus.EXCLUDED: 4},
        )
        for job, minutes, reason in (
            (done, 52, StopReason.COMPLETED),
            (paused, 61, StopReason.DAILY_LIMIT),
        ):
            start = job.created_at + timedelta(minutes=8)
            job.started_at = start
            if job.status is JobStatus.COMPLETED:
                job.finished_at = start + timedelta(minutes=minutes)
            db.add(EventLog(job_id=job.id, timestamp=start, message=RUN_STARTED_EVENT))
            db.add(
                EventLog(
                    job_id=job.id,
                    timestamp=start + timedelta(minutes=minutes),
                    message=STOP_MESSAGES[reason],
                )
            )
        db.add(DailyCounter(day=date.today(), unlike_count=150))
        db.commit()
        assert done.id is not None
        done_id = done.id
    write_report_files(engine, settings.reports_dir, done_id)
    engine.dispose()


def main() -> None:
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)
    settings = Settings(_env_file=None, data_dir=DEMO_DIR)
    settings.ensure_dirs()
    seed(settings)
    app = create_app(settings, token="demo")
    print(f"Démonstration (données fictives) : http://127.0.0.1:{PORT}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=PORT, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
