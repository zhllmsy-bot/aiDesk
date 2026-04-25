from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from api.auth.dependencies import require_session_context
from api.auth.models import User
from api.auth.schemas import SessionContextResponse
from api.database import get_db_session
from api.errors import unauthorized


def get_current_user(
    session_context: Annotated[SessionContextResponse, Depends(require_session_context)],
    session: Annotated[Session, Depends(get_db_session)],
) -> User:
    user = session.get(User, session_context.user.id)
    if user is None:
        raise unauthorized("Authenticated user no longer exists.")
    return user
