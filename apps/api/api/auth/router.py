from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from api.auth.dependencies import get_auth_service, require_session_context
from api.auth.schemas import CreateSessionRequest, RegisterUserRequest, SessionContextResponse
from api.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register", response_model=SessionContextResponse, status_code=status.HTTP_201_CREATED
)
def register(
    payload: RegisterUserRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionContextResponse:
    return auth_service.register(payload)


@router.post("/sessions", response_model=SessionContextResponse)
def create_session(
    payload: CreateSessionRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionContextResponse:
    return auth_service.login(payload)


@router.get("/me", response_model=SessionContextResponse)
def get_me(session_context: Annotated[SessionContextResponse, Depends(require_session_context)]):
    return session_context
