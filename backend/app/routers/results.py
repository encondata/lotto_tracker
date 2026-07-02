from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_admin
from app.models.draw import Draw
from app.models.reference import Game
from app.models.user import User
from app.results.matching import match_all_pending
from app.results.pipeline import run_pipeline
from app.services.draws import list_recent_draws, record_draw

router = APIRouter(prefix="/api/results", tags=["results"])


class DrawOut(BaseModel):
    id: str
    game_key: str
    draw_date: date
    draw_period: str | None
    winning_main: list[int]
    winning_special: int | None
    multiplier: int | None


class DrawCreate(BaseModel):
    game_key: str
    draw_date: date
    winning_main: list[int]
    winning_special: int | None = None
    multiplier: int | None = None
    payouts: dict | None = None
    draw_period: str | None = None


def _to_out(db: Session, draw: Draw, keys: dict) -> DrawOut:
    return DrawOut(
        id=str(draw.id),
        game_key=keys[draw.game_id],
        draw_date=draw.draw_date,
        draw_period=draw.draw_period,
        winning_main=draw.winning_main,
        winning_special=draw.winning_special,
        multiplier=draw.multiplier,
    )


def _game_keys(db: Session) -> dict:
    return {g.id: g.key for g in db.scalars(select(Game)).all()}


@router.get("/draws", response_model=list[DrawOut])
def get_draws(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    game_key: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query()] = 20,
) -> list[DrawOut]:
    draws = list_recent_draws(db, game_key=game_key, limit=limit)
    keys = _game_keys(db)
    return [_to_out(db, d, keys) for d in draws]


@router.post("/ingest")
def ingest(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> dict:
    summary = run_pipeline(db)
    db.commit()
    return summary


@router.post("/draws")
def post_draw(
    body: DrawCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> dict:
    try:
        draw = record_draw(
            db,
            body.game_key,
            body.draw_date,
            body.winning_main,
            winning_special=body.winning_special,
            multiplier=body.multiplier,
            payouts=body.payouts,
            draw_period=body.draw_period,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    results_created = match_all_pending(db)
    db.commit()
    keys = _game_keys(db)
    return {
        "draw": _to_out(db, draw, keys).model_dump(mode="json"),
        "results_created": results_created,
    }


@router.post("/match")
def post_match(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> dict:
    results_created = match_all_pending(db)
    db.commit()
    return {"results_created": results_created}
