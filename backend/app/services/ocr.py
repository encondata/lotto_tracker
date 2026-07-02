import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.reference import Game
from app.models.user import User
from app.ocr import get_provider
from app.ocr.base import OcrDraft
from app.services.tickets import validate_lines


def save_upload(user_id: uuid.UUID, filename: str, data: bytes) -> str:
    """Persist uploaded bytes under ``{media_dir}/{user_id}/{uuid}_{filename}``.

    Returns the path relative to ``media_dir``. Creates directories as needed.
    """
    media_dir = Path(get_settings().media_dir)
    safe_name = Path(filename or "upload").name  # strip any path components
    rel = Path(str(user_id)) / f"{uuid.uuid4().hex}_{safe_name}"
    dest = media_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return str(rel)


def scan_ticket(
    db: Session, user: User, filename: str, data: bytes
) -> OcrDraft:
    """Save the image, run the OCR provider, and return a validated DRAFT.

    Never creates a ticket and never raises on invalid extracted lines —
    validation problems are surfaced as ``flags`` for the confirmation UI.
    """
    image_path = save_upload(user.id, filename, data)

    draft = get_provider().extract(data, filename)
    draft.image_path = image_path

    if draft.game_key:
        game = db.scalar(select(Game).where(Game.key == draft.game_key))
        if game is None:
            draft.flags.append(f"Unknown game '{draft.game_key}'")
        elif draft.lines:
            try:
                validate_lines(game, draft.lines)
            except ValueError as exc:
                draft.flags.append(str(exc))

    return draft
