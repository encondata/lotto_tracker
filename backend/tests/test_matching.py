from datetime import date

from sqlalchemy import select

from app.models.draw import Draw, TicketResult
from app.models.reference import Game
from app.models.ticket import PlayLine, Ticket
from app.models.user import User
from app.results.matching import (
    applicable_draws,
    match_all_pending,
    match_ticket,
)
from app.security import hash_password
from app.seed import seed_reference_data
from app.services.draws import record_draw


def _game(db, key):
    return db.scalar(select(Game).where(Game.key == key))


def _user(db, email="u@example.com"):
    u = User(
        email=email,
        password_hash=hash_password("password123"),
        display_name="u",
        role="user",
    )
    db.add(u)
    db.flush()
    return u


def _ticket(db, user, game, lines, purchase_date=date(2026, 6, 1),
            num_draws=1, add_ons=None):
    t = Ticket(
        user_id=user.id,
        game_id=game.id,
        purchase_date=purchase_date,
        num_draws=num_draws,
        add_ons=add_ons or {},
        play_lines=[
            PlayLine(line_index=i, **ln) for i, ln in enumerate(lines)
        ],
    )
    db.add(t)
    db.flush()
    return t


def test_match_ticket_creates_won_result(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    record_draw(db_session, "powerball", date(2026, 6, 30),
                [1, 2, 3, 4, 5], winning_special=10, multiplier=2)
    db_session.flush()
    user = _user(db_session)
    t = _ticket(db_session, user, pb,
                [{"main_numbers": [1, 2, 3, 4, 8], "special_number": 10}])

    created = match_ticket(db_session, t)
    db_session.flush()
    assert created == 1
    results = db_session.scalars(select(TicketResult)).all()
    assert len(results) == 1
    r = results[0]
    assert r.status == "won"
    # 4 mains + PB -> tier 4+PB, base 5_000_000 cents
    assert r.tier_key == "4+PB"
    assert r.amount_won_cents == 5_000_000


def test_match_ticket_idempotent(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    record_draw(db_session, "powerball", date(2026, 6, 30),
                [1, 2, 3, 4, 5], winning_special=10)
    db_session.flush()
    user = _user(db_session)
    t = _ticket(db_session, user, pb,
                [{"main_numbers": [1, 2, 3, 4, 5], "special_number": 10}])
    assert match_ticket(db_session, t) == 1
    db_session.flush()
    assert match_ticket(db_session, t) == 0
    db_session.flush()
    assert len(db_session.scalars(select(TicketResult)).all()) == 1


def test_losing_line_is_no_win(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    record_draw(db_session, "powerball", date(2026, 6, 30),
                [1, 2, 3, 4, 5], winning_special=10)
    db_session.flush()
    user = _user(db_session)
    t = _ticket(db_session, user, pb,
                [{"main_numbers": [40, 41, 42, 43, 44], "special_number": 20}])
    match_ticket(db_session, t)
    db_session.flush()
    r = db_session.scalars(select(TicketResult)).one()
    assert r.status == "no_win"
    assert r.amount_won_cents == 0


def test_applicable_draws_respects_num_draws_and_date(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    # one before purchase, three after
    record_draw(db_session, "powerball", date(2026, 5, 30), [1, 2, 3, 4, 5],
                winning_special=1)
    record_draw(db_session, "powerball", date(2026, 6, 2), [1, 2, 3, 4, 5],
                winning_special=1)
    record_draw(db_session, "powerball", date(2026, 6, 4), [1, 2, 3, 4, 5],
                winning_special=1)
    record_draw(db_session, "powerball", date(2026, 6, 6), [1, 2, 3, 4, 5],
                winning_special=1)
    db_session.flush()
    user = _user(db_session)
    t = _ticket(db_session, user, pb,
                [{"main_numbers": [1, 2, 3, 4, 5], "special_number": 1}],
                purchase_date=date(2026, 6, 1), num_draws=2)
    draws = applicable_draws(db_session, t)
    assert len(draws) == 2
    assert [d.draw_date for d in draws] == [date(2026, 6, 2), date(2026, 6, 4)]


def test_pari_mutuel_amount_from_payouts(db_session):
    seed_reference_data(db_session)
    lt = _game(db_session, "lotto_texas")
    record_draw(db_session, "lotto_texas", date(2026, 6, 30),
                [1, 2, 3, 4, 5, 6], payouts={"5": 250000, "4": 5000})
    db_session.flush()
    user = _user(db_session)
    # match 5 of 6
    t = _ticket(db_session, user, lt,
                [{"main_numbers": [1, 2, 3, 4, 5, 40]}])
    match_ticket(db_session, t)
    db_session.flush()
    r = db_session.scalars(select(TicketResult)).one()
    assert r.status == "won"
    assert r.tier_key == "5"
    assert r.amount_won_cents == 250000


def test_match_all_pending(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    record_draw(db_session, "powerball", date(2026, 6, 30),
                [1, 2, 3, 4, 5], winning_special=10)
    db_session.flush()
    user = _user(db_session)
    _ticket(db_session, user, pb,
            [{"main_numbers": [1, 2, 3, 4, 5], "special_number": 10}])
    _ticket(db_session, user, pb,
            [{"main_numbers": [1, 2, 3, 44, 45], "special_number": 10}])
    total = match_all_pending(db_session)
    db_session.flush()
    assert total == 2
    # idempotent
    assert match_all_pending(db_session) == 0
