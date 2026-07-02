import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_pk


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"))
    purchase_date: Mapped[date]
    image_path: Mapped[str | None] = mapped_column(default=None)
    entry_method: Mapped[str] = mapped_column(default="manual")
    ocr_confidence: Mapped[float | None] = mapped_column(default=None)
    add_ons: Mapped[dict] = mapped_column(JSONB, default=dict)
    num_draws: Mapped[int] = mapped_column(default=1)
    total_cost_cents: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    play_lines: Mapped[list["PlayLine"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class PlayLine(Base):
    __tablename__ = "play_lines"

    id: Mapped[uuid.UUID] = uuid_pk()
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    line_index: Mapped[int]
    main_numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    special_number: Mapped[int | None] = mapped_column(default=None)
    play_type: Mapped[str | None] = mapped_column(default=None)
    wager_cents: Mapped[int] = mapped_column(default=0)
    is_quick_pick: Mapped[bool] = mapped_column(default=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="play_lines")
