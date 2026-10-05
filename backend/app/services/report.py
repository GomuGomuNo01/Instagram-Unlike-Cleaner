"""Rapport d'un nettoyage : bilan chiffré, durée, échecs, et exports CSV et JSON."""

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Engine
from sqlmodel import Session, col, select

from app.models.schemas import CleanupFilters
from app.models.tables import EventLog, ItemStatus, Job, JobStatus, LikedItem
from app.services.cleanup import RUN_INTERRUPTED_EVENT, RUN_STARTED_EVENT, STOP_MESSAGES
from app.services.jobs import STATUS_LABELS, JobActionRefused
from app.services.preview import kind_label

ITEM_STATUS_LABELS: dict[ItemStatus, str] = {
    ItemStatus.PENDING: "en attente",
    ItemStatus.SELECTED: "à retirer",
    ItemStatus.EXCLUDED: "exclu",
    ItemStatus.DONE: "retiré",
    ItemStatus.FAILED: "échec",
    ItemStatus.SKIPPED: "introuvable",
}
# Événements du journal qui ouvrent puis ferment une exécution. « Aperçu validé » ouvre
# aussi les exécutions antérieures au repère RUN_STARTED_EVENT.
_RUN_START_PREFIXES = (RUN_STARTED_EVENT, "Aperçu validé")
_RUN_END_PREFIXES = tuple(STOP_MESSAGES.values())


@dataclass(frozen=True)
class ReportLine:
    rank: int  # rang dans l'aperçu, à partir de 1
    author: str | None
    kind: str
    shared_on: str  # date « partagée le » selon Instagram, JJ/MM/AAAA
    status: ItemStatus
    processed_at: datetime | None
    detail: str | None
    media_key: str


@dataclass(frozen=True)
class JobReport:
    job_id: int
    status: JobStatus
    account_id: str | None
    filters: CleanupFilters
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    runs: int  # nombre d'exécutions (`iuc run`) du nettoyage
    active_time: timedelta  # temps passé à retirer, pauses entre exécutions exclues
    counts: dict[ItemStatus, int]
    lines: list[ReportLine]

    @property
    def targeted(self) -> int:
        return len(self.lines)

    @property
    def problems(self) -> list[ReportLine]:
        """Likes en échec ou introuvables, avec leur raison."""
        return [
            line for line in self.lines if line.status in (ItemStatus.FAILED, ItemStatus.SKIPPED)
        ]

    def to_dict(self) -> dict[str, Any]:
        """Version sérialisable en JSON, pour l'export et la future API."""
        return {
            "nettoyage": self.job_id,
            "statut": self.status.value,
            "compte": self.account_id,
            "criteres": self.filters.model_dump(mode="json"),
            "cree_le": _iso(self.created_at),
            "premiere_execution": _iso(self.started_at),
            "fin": _iso(self.finished_at),
            "executions": self.runs,
            "duree_active_secondes": round(self.active_time.total_seconds()),
            "likes_cibles": self.targeted,
            "par_statut": {status.value: count for status, count in self.counts.items()},
            "likes": [
                {
                    "rang": line.rank,
                    "auteur": line.author,
                    "type": line.kind,
                    "partagee_le": line.shared_on,
                    "statut": line.status.value,
                    "traite_le": _iso(line.processed_at),
                    "detail": line.detail,
                    "identifiant": line.media_key,
                }
                for line in self.lines
            ],
        }


def build_report(engine: Engine, job_id: int) -> JobReport:
    with Session(engine) as db:
        job = db.get(Job, job_id)
        if job is None:
            raise JobActionRefused(f"Aucun nettoyage n°{job_id}.")
        items = db.exec(
            select(LikedItem).where(LikedItem.job_id == job_id).order_by(col(LikedItem.position))
        ).all()
        events = db.exec(
            select(EventLog).where(EventLog.job_id == job_id).order_by(col(EventLog.id))
        ).all()
        lines = [
            ReportLine(
                rank=item.position + 1,
                author=item.author,
                kind=kind_label(item.media_kind),
                shared_on=item.published_on.strftime("%d/%m/%Y") if item.published_on else "",
                status=item.status,
                processed_at=item.processed_at,
                detail=item.error,
                media_key=item.media_key,
            )
            for item in items
        ]
        counts: dict[ItemStatus, int] = {}
        for line in lines:
            counts[line.status] = counts.get(line.status, 0) + 1
        runs, active_time = _run_times(events)
        return JobReport(
            job_id=job_id,
            status=job.status,
            account_id=job.account_id,
            filters=CleanupFilters.model_validate(job.filters),
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            runs=runs,
            active_time=active_time,
            counts=counts,
            lines=lines,
        )


def export_report_csv(report: JobReport, path: Path) -> Path:
    """Écrit le détail du rapport dans un CSV lisible par Excel (« ; », UTF-8 avec BOM)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(
            [
                "rang",
                "auteur",
                "type",
                "partagée le (selon Instagram)",
                "statut",
                "traité le",
                "détail",
                "identifiant",
            ]
        )
        for line in report.lines:
            writer.writerow(
                [
                    line.rank,
                    f"@{line.author}" if line.author else "",
                    line.kind,
                    line.shared_on,
                    ITEM_STATUS_LABELS[line.status],
                    _local(line.processed_at),
                    line.detail or "",
                    line.media_key,
                ]
            )
    return path


def export_report_json(report: JobReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_report_files(engine: Engine, reports_dir: Path, job_id: int) -> tuple[Path, Path]:
    """Écrit rapport-N.csv et rapport-N.json dans le dossier des rapports."""
    job_report = build_report(engine, job_id)
    return (
        export_report_csv(job_report, reports_dir / f"rapport-{job_id}.csv"),
        export_report_json(job_report, reports_dir / f"rapport-{job_id}.json"),
    )


def summary_lines(report: JobReport) -> list[str]:
    """Résumé lisible du rapport, une information par ligne."""
    counts = report.counts
    period = ""
    if report.started_at:
        end = _local(report.finished_at) if report.finished_at else "en cours"
        period = f", du {_local(report.started_at)} au {end}"
    return [
        f"Nettoyage n°{report.job_id} : {STATUS_LABELS[report.status]}{period}",
        f"  Likes ciblés : {report.targeted} | retirés : {counts.get(ItemStatus.DONE, 0)} | "
        f"échecs : {counts.get(ItemStatus.FAILED, 0)} | "
        f"introuvables : {counts.get(ItemStatus.SKIPPED, 0)} | "
        f"exclus : {counts.get(ItemStatus.EXCLUDED, 0)} | à traiter : "
        f"{counts.get(ItemStatus.PENDING, 0) + counts.get(ItemStatus.SELECTED, 0)}",
        f"  Durée active : {format_duration(report.active_time)} "
        f"en {report.runs} exécution{'s' if report.runs > 1 else ''}",
    ]


def format_duration(duration: timedelta) -> str:
    seconds = round(duration.total_seconds())
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours} h {minutes:02d} min"
    if minutes:
        return f"{minutes} min {seconds:02d} s"
    return f"{seconds} s"


def _run_times(events: Sequence[EventLog]) -> tuple[int, timedelta]:
    """Compte les exécutions et additionne leur durée, d'après les repères du journal."""
    runs = 0
    total = timedelta()
    started: datetime | None = None
    for event in events:
        if event.message.startswith(RUN_INTERRUPTED_EVENT):
            # Fin inconnue : l'exécution interrompue n'est pas comptée dans la durée.
            started = None
        elif event.message.startswith(_RUN_START_PREFIXES):
            if started is None:
                runs += 1
            started = started or event.timestamp
        elif event.message.startswith(_RUN_END_PREFIXES) and started is not None:
            total += event.timestamp - started
            started = None
    return runs, total


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _local(value: datetime | None) -> str:
    return value.astimezone().strftime("%d/%m/%Y %H:%M") if value else ""
