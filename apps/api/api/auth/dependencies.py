from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from api.auth.schemas import SessionContextResponse
from api.auth.service import AuthService
from api.database import get_db_session
from api.errors import unauthorized


def get_auth_service(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
) -> AuthService:
    return AuthService(session=session, settings=request.app.state.settings)


def _extract_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise unauthorized()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise unauthorized("Bearer token required.")
    return token.strip()


def require_session_context(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> SessionContextResponse:
    return auth_service.authenticate_token(_extract_bearer_token(authorization))
