"""Match tickets against recorded draws, producing TicketResult rows.

Uses the prize engine (:func:`app.prizes.engine.compute_win`) to resolve tier /
amount / status for each (play_line, draw) pair. All operations are idempotent:
a result is only created if none exists yet for that (play_line, draw).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.draw import Draw, TicketResult
from app.models.reference import Game
from app.models.ticket import Ticket
from app.prizes.engine import compute_win


def applicable_draws(db: Session, ticket: Ticket) -> list[Draw]:
    """Draws for the ticket's game on/after purchase_date, ordered
    (draw_date, draw_period NULLS FIRST), limited to num_draws."""
    stmt = (
        select(Draw)
        .where(
            Draw.game_id == ticket.game_id,
            Draw.draw_date >= ticket.purchase_date,
        )
        .order_by(Draw.draw_date.asc(), Draw.draw_period.asc().nullsfirst())
        .limit(ticket.num_draws)
    )
    return list(db.scalars(stmt).all())


def _existing_result(db: Session, play_line_id, draw_id) -> bool:
    return db.scalar(
        select(TicketResult.id).where(
            TicketResult.play_line_id == play_line_id,
            TicketResult.draw_id == draw_id,
        )
    ) is not None


def match_ticket(db: Session, ticket: Ticket) -> int:
    """Create missing TicketResults for each play_line x applicable draw.
    Returns the number of results created. Idempotent."""
    game = db.scalar(select(Game).where(Game.id == ticket.game_id))
    if game is None:
        return 0
    draws = applicable_draws(db, ticket)
    created = 0
    for line in ticket.play_lines:
        for draw in draws:
            if _existing_result(db, line.id, draw.id):
                continue
            win = compute_win(db, game, line, draw, ticket.add_ons or {})
            db.add(TicketResult(
                play_line_id=line.id,
                draw_id=draw.id,
                match_main_count=win.match_main,
                match_special=win.match_special,
                tier_key=win.tier_key,
                amount_won_cents=win.amount_cents,
                status=win.status,
            ))
            created += 1
    if created:
        db.flush()
    return created


def match_all_pending(db: Session) -> int:
    """Match every ticket (match_ticket is idempotent). Returns total created."""
    tickets = db.scalars(
        select(Ticket).options(selectinload(Ticket.play_lines))
    ).all()
    total = 0
    for ticket in tickets:
        total += match_ticket(db, ticket)
    return total
