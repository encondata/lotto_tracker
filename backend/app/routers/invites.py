from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.user import User
from app.services.invites import create_invite

router = APIRouter(prefix="/api/invites", tags=["invites"])


class InviteCreate(BaseModel):
    email: EmailStr


class InviteOut(BaseModel):
    token: str
    email: EmailStr
    expires_at: datetime


@router.post("/", response_model=InviteOut)
def create(
    body: InviteCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> InviteOut:
    invite = create_invite(db, body.email, admin.id)
    db.commit()
    return InviteOut(
        token=invite.token, email=invite.email, expires_at=invite.expires_at
    )
