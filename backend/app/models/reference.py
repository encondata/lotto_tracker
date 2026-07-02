import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_pk


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = uuid_pk()
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str]
    main_count: Mapped[int]
    main_min: Mapped[int]
    main_max: Mapped[int]
    has_special_ball: Mapped[bool] = mapped_column(default=False)
    special_min: Mapped[int | None] = mapped_column(default=None)
    special_max: Mapped[int | None] = mapped_column(default=None)
    base_price_cents: Mapped[int]
    prize_type: Mapped[str]
    draw_schedule: Mapped[dict] = mapped_column(JSONB, default=dict)

    prize_rules: Mapped[list["PrizeRule"]] = relationship(back_populates="game")


class PrizeRule(Base):
    __tablename__ = "prize_rules"
    __table_args__ = (UniqueConstraint("game_id", "tier_key", "play_type"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id"))
    tier_key: Mapped[str]
    match_main: Mapped[int]
    match_special: Mapped[bool] = mapped_column(default=False)
    play_type: Mapped[str | None] = mapped_column(default=None)
    base_amount_cents: Mapped[int | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(default=None)

    game: Mapped["Game"] = relationship(back_populates="prize_rules")
