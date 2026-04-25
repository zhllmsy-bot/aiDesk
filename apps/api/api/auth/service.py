from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth.models import ApiSession, User
from api.auth.repository import AuthRepository
from api.auth.schemas import (
    AuthenticatedUserModel,
    CreateSessionRequest,
    RegisterUserRequest,
    SessionContextResponse,
    SessionMembershipModel,
    SessionRecordModel,
)
from api.config import Settings
from api.errors import conflict, unauthorized

PASSWORD_HASH_ITERATIONS = 210_000


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return (
        f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}$"
        f"{salt.hex()}${digest.hex()}"
    )


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_hex, digest_hex = stored_hash.split("$", maxsplit=3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            iterations,
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def _is_expired(expires_at: datetime) -> bool:
    comparable = expires_at
    if comparable.tzinfo is None:
        comparable = comparable.replace(tzinfo=UTC)
    return comparable <= datetime.now(UTC)


class AuthService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._repository = AuthRepository(session)

    def register(self, payload: RegisterUserRequest) -> SessionContextResponse:
        email = _normalise_email(str(payload.email))
        if self._repository.get_user_by_email(email) is not None:
            raise conflict("A user with that email already exists.")

        user = User(
            email=email,
            display_name=payload.display_name,
            password_hash=_hash_password(payload.password),
            is_platform_admin=self._repository.count_users() == 0,
        )
        self._repository.add_user(user)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise conflict("A user with that email already exists.") from exc

        self._session.refresh(user)
        return self._create_session_context(user)

    def login(self, payload: CreateSessionRequest) -> SessionContextResponse:
        user = self._repository.get_user_by_email(_normalise_email(str(payload.email)))
        if user is None or not _verify_password(payload.password, user.password_hash):
            raise unauthorized("Invalid email or password.")
        return self._create_session_context(user)

    def authenticate_token(self, token: str) -> SessionContextResponse:
        token_hash = _hash_token(token)
        api_session = self._repository.get_api_session_by_token_hash(token_hash)
        if api_session is None or _is_expired(api_session.expires_at):
            raise unauthorized("Invalid or expired session.")
        return self._build_context(api_session=api_session, token=token)

    def _create_session_context(self, user: User) -> SessionContextResponse:
        raw_token = secrets.token_urlsafe(32)
        api_session = ApiSession(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(hours=self._settings.session_ttl_hours),
        )
        self._repository.add_api_session(api_session)
        self._session.commit()
        self._session.refresh(api_session)
        api_session.user = user
        return self._build_context(api_session=api_session, token=raw_token)

    def _build_context(self, api_session: ApiSession, token: str) -> SessionContextResponse:
        user = api_session.user
        memberships = [
            SessionMembershipModel(
                project_id=project.id,
                project_name=project.name,
                role=membership.role,
                status=membership.status,
            )
            for membership, project in self._repository.list_active_memberships_for_user(user.id)
        ]
        return SessionContextResponse(
            session=SessionRecordModel(
                id=api_session.id,
                expires_at=api_session.expires_at,
                token=token,
            ),
            user=AuthenticatedUserModel.model_validate(user),
            memberships=memberships,
        )
