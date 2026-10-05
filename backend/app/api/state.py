"""État partagé de l'API : navigateur unique, tâche de fond unique et diffusion d'événements.

Un seul Chromium tourne à la fois, et une seule tâche (collecte d'aperçu ou nettoyage)
l'utilise à la fois : deux tâches simultanées se disputeraient la même page Instagram.
"""

import asyncio
import contextlib
import itertools
import logging
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import Engine

from app.browser.session import CLOSED_STATUS, BrowserSession, SessionStatus
from app.core.config import Settings
from app.services.cleanup import CleanupControl

logger = logging.getLogger(__name__)

BrowserFactory = Callable[[Path], BrowserSession]
TaskKind = Literal["preview", "cleanup"]


class ApiConflict(RuntimeError):
    """Action impossible dans l'état actuel (navigateur fermé, tâche en cours...)."""


@dataclass(frozen=True)
class ServerEvent:
    id: int
    type: str
    data: dict[str, Any]


class EventHub:
    """Diffuse les événements d'un nettoyage à ses abonnés (flux SSE).

    Les derniers événements de chaque nettoyage sont conservés : un abonné qui arrive en
    cours de route, ou qui se reconnecte, reçoit d'abord cet historique.
    """

    def __init__(self, history: int = 500) -> None:
        self._ids = itertools.count(1)
        self._history: dict[int, deque[ServerEvent]] = defaultdict(lambda: deque(maxlen=history))
        self._subscribers: dict[int, set[asyncio.Queue[ServerEvent]]] = defaultdict(set)

    def publish(self, job_id: int, type_: str, data: dict[str, Any]) -> ServerEvent:
        event = ServerEvent(next(self._ids), type_, data)
        self._history[job_id].append(event)
        for queue in self._subscribers[job_id]:
            queue.put_nowait(event)
        return event

    def history(self, job_id: int) -> list[ServerEvent]:
        return list(self._history[job_id])

    @contextlib.asynccontextmanager
    async def subscribe(
        self, job_id: int
    ) -> AsyncIterator[tuple[list[ServerEvent], asyncio.Queue[ServerEvent]]]:
        queue: asyncio.Queue[ServerEvent] = asyncio.Queue()
        self._subscribers[job_id].add(queue)
        try:
            yield self.history(job_id), queue
        finally:
            self._subscribers[job_id].discard(queue)


class BrowserManager:
    """Ouvre, surveille et ferme l'unique navigateur piloté par l'API."""

    def __init__(self, settings: Settings, factory: BrowserFactory) -> None:
        self._settings = settings
        self._factory = factory
        self._session: BrowserSession | None = None
        self._lock = asyncio.Lock()

    @property
    def session(self) -> BrowserSession:
        """Navigateur ouvert, ou ApiConflict s'il ne l'est pas."""
        if self._session is None or not self._session.is_open:
            raise ApiConflict("Le navigateur n'est pas ouvert : lance d'abord la session.")
        return self._session

    async def start(self) -> SessionStatus:
        """Ouvre le navigateur sur l'accueil d'Instagram, s'il ne l'est pas déjà."""
        async with self._lock:
            if self._session is not None and not self._session.is_open:
                # Fenêtre fermée par l'utilisateur : on libère Playwright avant de relancer.
                await self._session.close()
                self._session = None
            if self._session is None:
                session = self._factory(self._settings.browser_profile_dir)
                await session.start()
                self._session = session
                await session.open_home()
        return await self.status()

    async def status(self) -> SessionStatus:
        if self._session is None:
            return CLOSED_STATUS
        return await self._session.status()

    async def close(self) -> None:
        async with self._lock:
            if self._session is not None:
                await self._session.close()
                self._session = None


@dataclass
class RunningTask:
    job_id: int
    kind: TaskKind
    task: asyncio.Task[None]
    control: CleanupControl = field(default_factory=CleanupControl)


class TaskRunner:
    """Exécute en arrière-plan une tâche à la fois et garde la trace de la tâche en cours."""

    def __init__(self) -> None:
        self.current: RunningTask | None = None

    @property
    def busy(self) -> bool:
        return self.current is not None and not self.current.task.done()

    def running_for(self, job_id: int) -> RunningTask | None:
        if self.busy and self.current is not None and self.current.job_id == job_id:
            return self.current
        return None

    def launch(
        self,
        job_id: int,
        kind: TaskKind,
        work: Callable[[CleanupControl], Coroutine[Any, Any, None]],
    ) -> RunningTask:
        if self.busy:
            assert self.current is not None
            raise ApiConflict(
                f"Une tâche est déjà en cours (nettoyage n°{self.current.job_id}) : "
                "attends sa fin ou mets-la en pause."
            )
        control = CleanupControl()
        task = asyncio.create_task(work(control), name=f"iuc-{kind}-{job_id}")
        self.current = RunningTask(job_id, kind, task, control)
        return self.current

    async def wait(self) -> None:
        """Attend la fin de la tâche en cours (utile aux tests et à l'arrêt du serveur)."""
        if self.current is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await self.current.task

    async def cancel(self) -> None:
        if self.busy and self.current is not None:
            self.current.task.cancel()
            await self.wait()


@dataclass
class ApiState:
    settings: Settings
    engine: Engine
    token: str
    browser: BrowserManager
    runner: TaskRunner = field(default_factory=TaskRunner)
    hub: EventHub = field(default_factory=EventHub)
