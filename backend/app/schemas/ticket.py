import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class PlayLineIn(BaseModel):
    main_numbers: list[int]
    special_number: int | None = None
    play_type: str | None = None
    wager_cents: int = 0
    is_quick_pick: bool = False


class TicketCreate(BaseModel):
    game_key: str
    purchase_date: date
    num_draws: int = 1
    add_ons: dict = Field(default_factory=dict)
    entry_method: str = "manual"
    lines: list[PlayLineIn] = Field(min_length=1)


class PlayLineOut(BaseModel):
    id: uuid.UUID
    line_index: int
    main_numbers: list[int]
    special_number: int | None = None
    play_type: str | None = None
    wager_cents: int
    is_quick_pick: bool

    model_config = {"from_attributes": True}


class TicketResultOut(BaseModel):
    tier_key: str | None
    match_main_count: int
    match_special: bool
    amount_won_cents: int
    status: str
    draw_id: uuid.UUID

    model_config = {"from_attributes": True}


class TicketOut(BaseModel):
    id: uuid.UUID
    game_key: str
    purchase_date: date
    num_draws: int
    add_ons: dict
    entry_method: str
    total_cost_cents: int
    created_at: datetime
    lines: list[PlayLineOut]
    results: list[TicketResultOut]
    total_won_cents: int
