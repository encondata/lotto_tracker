from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services import analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def get_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> dict:
    return analytics.summary(db, user, date_from=date_from, date_to=date_to)


@router.get("/by-game")
def get_by_game(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[dict]:
    return analytics.by_game(db, user, date_from=date_from, date_to=date_to)


@router.get("/over-time")
def get_over_time(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    bucket: Annotated[str, Query(pattern="^(month|week)$")] = "month",
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[dict]:
    return analytics.over_time(
        db, user, date_from=date_from, date_to=date_to, bucket=bucket
    )


@router.get("/pick-breakdown")
def get_pick_breakdown(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> dict:
    return analytics.pick_breakdown(db, user, date_from=date_from, date_to=date_to)
