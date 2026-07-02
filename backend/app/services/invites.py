import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import Invite

INVITE_TTL_DAYS = 7


class InviteError(Exception):
    """Raised when an invite cannot be accepted."""


def _aware(dt: datetime) -> datetime:
    """Treat naive timestamps (from the DB) as UTC for comparison."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def create_invite(db: Session, email: str, invited_by: uuid.UUID) -> Invite:
    invite = Invite(
        email=email,
        token=secrets.token_urlsafe(32),
        invited_by=invited_by,
        expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invite)
    db.flush()
    return invite


def accept_invite(db: Session, token: str, email: str) -> Invite:
    invite = db.scalar(select(Invite).where(Invite.token == token))
    if invite is None:
        raise InviteError("Invite not found")
    if invite.accepted_at is not None:
        raise InviteError("Invite already used")
    if _aware(invite.expires_at) < datetime.now(timezone.utc):
        raise InviteError("Invite expired")
    if invite.email.lower() != email.lower():
        raise InviteError("Invite email mismatch")
    invite.accepted_at = datetime.now(timezone.utc)
    db.flush()
    return invite
