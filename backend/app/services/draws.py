"""Manual draw entry and recent-draw listing."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.draw import Draw
from app.models.reference import Game


def _get_game(db: Session, game_key: str) -> Game:
    game = db.scalar(select(Game).where(Game.key == game_key))
    if game is None:
        raise ValueError(f"Unknown game '{game_key}'")
    return game


def _find_draw(db: Session, game_id, draw_date, draw_period) -> Draw | None:
    stmt = select(Draw).where(
        Draw.game_id == game_id,
        Draw.draw_date == draw_date,
    )
    if draw_period is None:
        stmt = stmt.where(Draw.draw_period.is_(None))
    else:
        stmt = stmt.where(Draw.draw_period == draw_period)
    return db.scalar(stmt)


def record_draw(
    db: Session,
    game_key: str,
    draw_date: date,
    winning_main: list[int],
    winning_special: int | None = None,
    multiplier: int | None = None,
    payouts: dict | None = None,
    draw_period: str | None = None,
    source: str = "manual",
) -> Draw:
    """Upsert a draw for (game, date, period). Updates existing, returns Draw."""
    game = _get_game(db, game_key)
    draw = _find_draw(db, game.id, draw_date, draw_period)
    if draw is None:
        draw = Draw(
            game_id=game.id,
            draw_date=draw_date,
            draw_period=draw_period,
        )
        db.add(draw)
    draw.winning_main = list(winning_main)
    draw.winning_special = winning_special
    draw.multiplier = multiplier
    draw.payouts = payouts
    draw.source = source
    db.flush()
    return draw


def list_recent_draws(
    db: Session, game_key: str | None = None, limit: int = 20
) -> list[Draw]:
    """Return newest-first recent draws, optionally filtered by game."""
    stmt = select(Draw).order_by(
        Draw.draw_date.desc(), Draw.ingested_at.desc()
    ).limit(limit)
    if game_key is not None:
        game = db.scalar(select(Game).where(Game.key == game_key))
        if game is None:
            return []
        stmt = stmt.where(Draw.game_id == game.id)
    return list(db.scalars(stmt).all())
