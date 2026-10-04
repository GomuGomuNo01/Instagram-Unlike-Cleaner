import pytest

from app.models.tables import JOB_TRANSITIONS, JobStatus, can_transition

TERMINAL = {JobStatus.COMPLETED, JobStatus.STOPPED, JobStatus.FAILED}


def test_every_status_has_transitions_defined() -> None:
    assert set(JOB_TRANSITIONS) == set(JobStatus)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (JobStatus.CREATED, JobStatus.COLLECTING),
        (JobStatus.COLLECTING, JobStatus.READY),
        (JobStatus.READY, JobStatus.RUNNING),
        (JobStatus.RUNNING, JobStatus.PAUSED),
        (JobStatus.PAUSED, JobStatus.RUNNING),
        (JobStatus.RUNNING, JobStatus.COMPLETED),
        (JobStatus.PAUSED, JobStatus.STOPPED),
    ],
)
def test_allowed_transitions(current: JobStatus, target: JobStatus) -> None:
    assert can_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (JobStatus.CREATED, JobStatus.RUNNING),  # pas d'unlike sans aperçu
        (JobStatus.COLLECTING, JobStatus.RUNNING),  # pas d'unlike sans validation de l'aperçu
        (JobStatus.READY, JobStatus.COMPLETED),
    ],
)
def test_forbidden_transitions(current: JobStatus, target: JobStatus) -> None:
    assert not can_transition(current, target)


@pytest.mark.parametrize("status", sorted(TERMINAL))
def test_terminal_statuses_have_no_way_out(status: JobStatus) -> None:
    assert JOB_TRANSITIONS[status] == frozenset()
