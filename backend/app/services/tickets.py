import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.draw import TicketResult
from app.models.reference import Game
from app.models.ticket import PlayLine, Ticket
from app.models.user import User
from app.prizes.cost import ticket_cost_cents
from app.schemas.ticket import (
    PlayLineOut,
    TicketCreate,
    TicketOut,
    TicketResultOut,
)

DAILY_KEYS = {"daily4"}
DAILY4_PLAY_TYPES = {
    "straight",
    "box",
    "combo",
    "pair-front",
    "pair-mid",
    "pair-back",
}


def validate_lines(game: Game, lines) -> None:
    """Validate play lines against per-game rules; raise ValueError on violation.

    ``lines`` is an iterable of objects/schemas exposing ``main_numbers``,
    ``special_number`` and ``play_type``.
    """
    for idx, line in enumerate(lines):
        main = list(line.main_numbers)
        if game.key in DAILY_KEYS:
            _validate_daily4_line(game, line, main, idx)
        else:
            _validate_jackpot_line(game, line, main, idx)


def _validate_daily4_line(game: Game, line, main: list[int], idx: int) -> None:
    if len(main) != 4:
        raise ValueError(
            f"line {idx}: daily4 requires exactly 4 digits, got {len(main)}"
        )
    for d in main:
        if d < 0 or d > 9:
            raise ValueError(
                f"line {idx}: daily4 digits must be within 0-9, got {d}"
            )
    play_type = line.play_type
    if play_type is None:
        raise ValueError(f"line {idx}: daily4 requires a play_type")
    if play_type not in DAILY4_PLAY_TYPES:
        raise ValueError(
            f"line {idx}: invalid play_type '{play_type}'; "
            f"must be one of {sorted(DAILY4_PLAY_TYPES)}"
        )


def _validate_jackpot_line(game: Game, line, main: list[int], idx: int) -> None:
    if len(main) != game.main_count:
        raise ValueError(
            f"line {idx}: {game.key} requires exactly {game.main_count} "
            f"main numbers, got {len(main)}"
        )
    if len(set(main)) != len(main):
        raise ValueError(f"line {idx}: main numbers must be distinct")
    for n in main:
        if n < game.main_min or n > game.main_max:
            raise ValueError(
                f"line {idx}: main number {n} outside range "
                f"[{game.main_min}, {game.main_max}]"
            )
    if game.has_special_ball:
        special = line.special_number
        if special is None:
            raise ValueError(f"line {idx}: {game.key} requires a special number")
        if special < game.special_min or special > game.special_max:
            raise ValueError(
                f"line {idx}: special number {special} outside range "
                f"[{game.special_min}, {game.special_max}]"
            )


def _get_game(db: Session, game_key: str) -> Game:
    game = db.scalar(select(Game).where(Game.key == game_key))
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown game '{game_key}'",
        )
    return game


def create_ticket(db: Session, user: User, data: TicketCreate) -> Ticket:
    game = _get_game(db, data.game_key)
    validate_lines(game, data.lines)

    play_lines = [
        PlayLine(
            line_index=i,
            main_numbers=list(line.main_numbers),
            special_number=line.special_number,
            play_type=line.play_type,
            wager_cents=line.wager_cents,
            is_quick_pick=line.is_quick_pick,
        )
        for i, line in enumerate(data.lines)
    ]

    total_cost_cents = ticket_cost_cents(
        game, play_lines, data.add_ons, data.num_draws
    )

    ticket = Ticket(
        user_id=user.id,
        game_id=game.id,
        purchase_date=data.purchase_date,
        entry_method=data.entry_method,
        add_ons=data.add_ons or {},
        num_draws=data.num_draws,
        total_cost_cents=total_cost_cents,
        play_lines=play_lines,
    )
    db.add(ticket)
    db.flush()
    db.refresh(ticket)
    return ticket


def list_tickets(
    db: Session,
    user: User,
    game_key: str | None = None,
    status: str | None = None,
) -> list[Ticket]:
    stmt = (
        select(Ticket)
        .where(Ticket.user_id == user.id)
        .options(selectinload(Ticket.play_lines))
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
    )
    if game_key is not None:
        game = db.scalar(select(Game).where(Game.key == game_key))
        if game is None:
            return []
        stmt = stmt.where(Ticket.game_id == game.id)
    tickets = list(db.scalars(stmt).all())

    if status is not None:
        filtered = []
        for t in tickets:
            results = _results_for_ticket(db, t)
            if any(r.status == status for r in results):
                filtered.append(t)
        tickets = filtered
    return tickets


def get_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> Ticket:
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(selectinload(Ticket.play_lines))
    )
    if ticket is None or ticket.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
        )
    return ticket


def delete_ticket(db: Session, user: User, ticket_id: uuid.UUID) -> None:
    ticket = get_ticket(db, user, ticket_id)
    db.delete(ticket)
    db.flush()


def _results_for_ticket(db: Session, ticket: Ticket) -> list[TicketResult]:
    line_ids = [line.id for line in ticket.play_lines]
    if not line_ids:
        return []
    return list(
        db.scalars(
            select(TicketResult).where(TicketResult.play_line_id.in_(line_ids))
        ).all()
    )


def to_ticket_out(db: Session, ticket: Ticket, game: Game) -> TicketOut:
    lines = sorted(ticket.play_lines, key=lambda ln: ln.line_index)
    results = _results_for_ticket(db, ticket)
    total_won_cents = sum(r.amount_won_cents for r in results)
    return TicketOut(
        id=ticket.id,
        game_key=game.key,
        purchase_date=ticket.purchase_date,
        num_draws=ticket.num_draws,
        add_ons=ticket.add_ons or {},
        entry_method=ticket.entry_method,
        total_cost_cents=ticket.total_cost_cents,
        created_at=ticket.created_at,
        lines=[PlayLineOut.model_validate(ln) for ln in lines],
        results=[TicketResultOut.model_validate(r) for r in results],
        total_won_cents=total_won_cents,
    )
