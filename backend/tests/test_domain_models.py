from datetime import date, datetime, timedelta, UTC

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.reference import Game
from app.models.user import User, Invite
from app.models.ticket import Ticket, PlayLine
from app.models.draw import Draw, TicketResult, IngestionRun


def _game(db):
    g = Game(key="lotto_texas", display_name="Lotto Texas", main_count=6,
             main_min=1, main_max=54, base_price_cents=100, prize_type="pari_mutuel",
             draw_schedule={"days": ["Mon", "Wed", "Sat"]})
    db.add(g)
    db.flush()
    return g


def test_ticket_with_lines_and_result(db_session):
    g = _game(db_session)
    user = User(email="a@b.com", password_hash="x", display_name="A")
    db_session.add(user)
    db_session.flush()

    ticket = Ticket(user_id=user.id, game_id=g.id, purchase_date=date(2026, 7, 1),
                    num_draws=2, total_cost_cents=200,
                    play_lines=[PlayLine(line_index=0, main_numbers=[1, 2, 3, 4, 5, 6],
                                         wager_cents=100)])
    db_session.add(ticket)
    db_session.flush()
    assert ticket.play_lines[0].main_numbers == [1, 2, 3, 4, 5, 6]

    draw = Draw(game_id=g.id, draw_date=date(2026, 7, 2),
                winning_main=[1, 2, 3, 9, 10, 11], source="csv")
    db_session.add(draw)
    db_session.flush()

    res = TicketResult(play_line_id=ticket.play_lines[0].id, draw_id=draw.id,
                       match_main_count=3, tier_key="match3",
                       amount_won_cents=300, status="won")
    db_session.add(res)
    db_session.flush()
    assert res.status == "won"


def test_draw_unique_constraint(db_session):
    g = _game(db_session)
    db_session.add(Draw(game_id=g.id, draw_date=date(2026, 7, 2), winning_main=[1]))
    db_session.flush()
    db_session.add(Draw(game_id=g.id, draw_date=date(2026, 7, 2), winning_main=[2]))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invite_and_ingestion_run(db_session):
    g = _game(db_session)
    admin = User(email="admin@b.com", password_hash="x", display_name="Admin", role="admin")
    db_session.add(admin)
    db_session.flush()
    inv = Invite(email="new@b.com", token="tok123", invited_by=admin.id,
                 expires_at=datetime.now(UTC) + timedelta(days=7))
    run = IngestionRun(game_id=g.id, status="success", rows_added=3)
    db_session.add_all([inv, run])
    db_session.flush()
    assert inv.accepted_at is None and run.rows_added == 3
