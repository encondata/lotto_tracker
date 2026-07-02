import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class Draw(Base):
    __tablename__ = "draws"
    # NULLS NOT DISTINCT: treat NULL draw_period (all non-Daily-4 games) as equal,
    # so the constraint actually blocks duplicate draws. Requires Postgres 15+.
    __table_args__ = (
        UniqueConstraint(
            "game_id", "draw_date", "draw_period",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"), index=True)
    draw_date: Mapped[date] = mapped_column(index=True)
    draw_period: Mapped[str | None] = mapped_column(default=None)
    winning_main: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    winning_special: Mapped[int | None] = mapped_column(default=None)
    multiplier: Mapped[int | None] = mapped_column(default=None)
    payouts: Mapped[dict | None] = mapped_column(JSONB, default=None)
    source: Mapped[str] = mapped_column(default="csv")
    ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())


class TicketResult(Base):
    __tablename__ = "ticket_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    play_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("play_lines.id", ondelete="CASCADE"), index=True
    )
    draw_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("draws.id"), index=True)
    match_main_count: Mapped[int] = mapped_column(default=0)
    match_special: Mapped[bool] = mapped_column(default=False)
    tier_key: Mapped[str | None] = mapped_column(default=None)
    amount_won_cents: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(default="pending")
    computed_at: Mapped[datetime] = mapped_column(server_default=func.now())


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"))
    status: Mapped[str]
    rows_added: Mapped[int] = mapped_column(default=0)
    errors: Mapped[str | None] = mapped_column(default=None)
    ran_at: Mapped[datetime] = mapped_column(server_default=func.now())
