from datetime import date

from app.ocr import get_provider
from app.ocr.base import OcrDraft
from app.ocr.mock import MockOcrProvider
from app.schemas.ticket import PlayLineIn
from app.seed import seed_reference_data
from app.services.tickets import validate_lines
from sqlalchemy import select

from app.models.reference import Game


def test_extract_returns_draft_shape():
    draft = MockOcrProvider().extract(b"\xff\xd8\xff\x00", "t.jpg")
    assert isinstance(draft, OcrDraft)
    assert draft.game_key == "powerball"
    assert draft.purchase_date == date.today()
    assert len(draft.lines) == 2
    assert all(isinstance(ln, PlayLineIn) for ln in draft.lines)
    assert draft.add_ons == {"power_play": True}


def test_extract_lines_pass_validate_lines(db_session):
    seed_reference_data(db_session)
    game = db_session.scalar(select(Game).where(Game.key == "powerball"))
    draft = MockOcrProvider().extract(b"some-image-bytes", "photo.png")
    # Must not raise.
    validate_lines(game, draft.lines)


def test_confidence_populated_and_in_range():
    draft = MockOcrProvider().extract(b"abc", "t.jpg")
    assert draft.confidence
    for key, val in draft.confidence.items():
        assert 0.0 <= val <= 1.0
    assert draft.flags == []


def test_deterministic_for_same_input():
    a = MockOcrProvider().extract(b"same-bytes-1234", "t.jpg")
    b = MockOcrProvider().extract(b"same-bytes-1234", "t.jpg")
    assert [ln.main_numbers for ln in a.lines] == [ln.main_numbers for ln in b.lines]


def test_varies_by_image_length():
    a = MockOcrProvider().extract(b"x" * 10, "t.jpg")
    b = MockOcrProvider().extract(b"x" * 5000, "t.jpg")
    # Different lengths should generally produce different mains.
    assert [ln.main_numbers for ln in a.lines] != [
        ln.main_numbers for ln in b.lines
    ]


def test_has_a_quick_pick_line():
    draft = MockOcrProvider().extract(b"abc", "t.jpg")
    assert any(ln.is_quick_pick for ln in draft.lines)


def test_get_provider_returns_mock():
    assert isinstance(get_provider(), MockOcrProvider)
