from datetime import date
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.schemas.ticket import PlayLineIn


class OcrField(BaseModel):
    """A single extracted value with a confidence score (0.0-1.0).

    The :class:`OcrDraft` uses a flat ``confidence`` map instead of wrapping
    every field, but this type is provided for callers/providers that want to
    return per-value confidence explicitly.
    """

    value: object = None
    confidence: float = 0.0


class OcrDraft(BaseModel):
    """A DRAFT ticket extracted from a photo.

    Shaped to line up with :class:`app.schemas.ticket.TicketCreate` so the
    frontend can pre-fill a confirmation form and, after the user confirms,
    POST it to ``/api/tickets``. OCR never creates a ticket itself.
    """

    game_key: str | None = None
    purchase_date: date | None = None
    num_draws: int = 1
    add_ons: dict = Field(default_factory=dict)
    lines: list[PlayLineIn] = Field(default_factory=list)
    # field name -> confidence (0.0-1.0)
    confidence: dict[str, float] = Field(default_factory=dict)
    # human-readable issues for the confirm UI (e.g. validation warnings)
    flags: list[str] = Field(default_factory=list)
    raw_text: str | None = None
    # relative path of the stored source image, set by the scan service.
    image_path: str | None = None


@runtime_checkable
class OcrProvider(Protocol):
    """Extracts a draft ticket from an image. Implementations must be pure
    with respect to the DB — validation against games happens in the service
    layer, not the provider."""

    def extract(self, image_bytes: bytes, filename: str) -> OcrDraft:
        ...
