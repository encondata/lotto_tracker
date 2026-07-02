import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.reference import Game
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketOut
from app.services.tickets import (
    create_ticket,
    delete_ticket,
    get_ticket,
    list_tickets,
    to_ticket_out,
)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _game_for(db: Session, ticket) -> Game:
    return db.scalar(select(Game).where(Game.id == ticket.game_id))


@router.post("/", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create(
    body: TicketCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> TicketOut:
    try:
        ticket = create_ticket(db, user, body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    db.commit()
    game = _game_for(db, ticket)
    out = to_ticket_out(db, ticket, game)
    return out


@router.get("/", response_model=list[TicketOut])
def index(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    game_key: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[TicketOut]:
    tickets = list_tickets(db, user, game_key=game_key, status=status_filter)
    out = []
    for ticket in tickets:
        game = _game_for(db, ticket)
        out.append(to_ticket_out(db, ticket, game))
    return out


@router.get("/{ticket_id}", response_model=TicketOut)
def detail(
    ticket_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> TicketOut:
    ticket = get_ticket(db, user, ticket_id)
    game = _game_for(db, ticket)
    return to_ticket_out(db, ticket, game)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    ticket_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    delete_ticket(db, user, ticket_id)
    db.commit()
