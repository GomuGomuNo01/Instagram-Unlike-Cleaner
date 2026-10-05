"""Dépendances communes aux routes de l'API."""

from typing import Annotated

from fastapi import Depends, Request

from app.api.state import ApiState


def get_state(request: Request) -> ApiState:
    state: ApiState = request.app.state.iuc
    return state


StateDep = Annotated[ApiState, Depends(get_state)]
