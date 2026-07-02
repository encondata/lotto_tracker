import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.draw import Draw, TicketResult
from app.models.reference import Game
from app.models.user import User
from app.prizes.cost import ticket_cost_cents
from app.schemas.ticket import PlayLineIn, TicketCreate
from app.seed import seed_reference_data
from app.security import hash_password
from app.services.tickets import (
    create_ticket,
    delete_ticket,
    get_ticket,
    list_tickets,
    to_ticket_out,
    validate_lines,
)


def _game(db_session, key):
    return db_session.scalar(select(Game).where(Game.key == key))


def _user(db_session, email):
    u = User(
        email=email,
        password_hash=hash_password("password123"),
        display_name=email.split("@")[0],
        role="user",
    )
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def seeded(db_session):
    seed_reference_data(db_session)
    return db_session


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def test_validate_jackpot_happy(seeded):
    pb = _game(seeded, "powerball")
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 4, 5], special_number=10)]
    validate_lines(pb, lines)  # should not raise


def test_validate_jackpot_wrong_count(seeded):
    pb = _game(seeded, "powerball")
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 4], special_number=10)]
    with pytest.raises(ValueError):
        validate_lines(pb, lines)


def test_validate_jackpot_non_distinct(seeded):
    pb = _game(seeded, "powerball")
    lines = [PlayLineIn(main_numbers=[1, 1, 3, 4, 5], special_number=10)]
    with pytest.raises(ValueError):
        validate_lines(pb, lines)


def test_validate_jackpot_out_of_range_main(seeded):
    pb = _game(seeded, "powerball")  # main_max=69
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 4, 99], special_number=10)]
    with pytest.raises(ValueError):
        validate_lines(pb, lines)


def test_validate_jackpot_special_required(seeded):
    pb = _game(seeded, "powerball")
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 4, 5])]
    with pytest.raises(ValueError):
        validate_lines(pb, lines)


def test_validate_jackpot_special_out_of_range(seeded):
    pb = _game(seeded, "powerball")  # special_max=26
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 4, 5], special_number=99)]
    with pytest.raises(ValueError):
        validate_lines(pb, lines)


def test_validate_no_special_game(seeded):
    lt = _game(seeded, "lotto_texas")  # has_special_ball False, main_count 6
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 4, 5, 6])]
    validate_lines(lt, lines)  # no special required


def test_validate_daily4_happy(seeded):
    d4 = _game(seeded, "daily4")
    lines = [PlayLineIn(main_numbers=[0, 3, 3, 9], play_type="box")]
    validate_lines(d4, lines)


def test_validate_daily4_repeats_allowed(seeded):
    d4 = _game(seeded, "daily4")
    lines = [PlayLineIn(main_numbers=[7, 7, 7, 7], play_type="straight")]
    validate_lines(d4, lines)  # repeats allowed


def test_validate_daily4_wrong_length(seeded):
    d4 = _game(seeded, "daily4")
    lines = [PlayLineIn(main_numbers=[1, 2, 3], play_type="straight")]
    with pytest.raises(ValueError):
        validate_lines(d4, lines)


def test_validate_daily4_digit_out_of_range(seeded):
    d4 = _game(seeded, "daily4")
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 10], play_type="straight")]
    with pytest.raises(ValueError):
        validate_lines(d4, lines)


def test_validate_daily4_play_type_required(seeded):
    d4 = _game(seeded, "daily4")
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 4])]
    with pytest.raises(ValueError):
        validate_lines(d4, lines)


def test_validate_daily4_bad_play_type(seeded):
    d4 = _game(seeded, "daily4")
    lines = [PlayLineIn(main_numbers=[1, 2, 3, 4], play_type="nope")]
    with pytest.raises(ValueError):
        validate_lines(d4, lines)


# --------------------------------------------------------------------------
# create + cost
# --------------------------------------------------------------------------

def test_create_computes_cost_powerball(seeded):
    user = _user(seeded, "a@example.com")
    pb = _game(seeded, "powerball")
    data = TicketCreate(
        game_key="powerball",
        purchase_date=date(2026, 1, 1),
        num_draws=2,
        add_ons={"power_play": True},
        lines=[
            PlayLineIn(main_numbers=[1, 2, 3, 4, 5], special_number=10),
            PlayLineIn(main_numbers=[6, 7, 8, 9, 10], special_number=11),
        ],
    )
    ticket = create_ticket(seeded, user, data)
    expected = ticket_cost_cents(pb, ticket.play_lines, {"power_play": True}, 2)
    assert ticket.total_cost_cents == expected
    assert ticket.total_cost_cents == (200 + 100) * 2 * 2  # 1200
    assert len(ticket.play_lines) == 2
    assert [ln.line_index for ln in sorted(ticket.play_lines, key=lambda x: x.line_index)] == [0, 1]


def test_create_computes_cost_daily4(seeded):
    user = _user(seeded, "b@example.com")
    d4 = _game(seeded, "daily4")
    data = TicketCreate(
        game_key="daily4",
        purchase_date=date(2026, 1, 1),
        num_draws=1,
        add_ons={"fireball": True},
        lines=[PlayLineIn(main_numbers=[1, 2, 3, 4], play_type="straight", wager_cents=100)],
    )
    ticket = create_ticket(seeded, user, data)
    assert ticket.total_cost_cents == 200  # 100 * 2 fireball


def test_create_unknown_game_404(seeded):
    from fastapi import HTTPException

    user = _user(seeded, "c@example.com")
    data = TicketCreate(
        game_key="nope",
        purchase_date=date(2026, 1, 1),
        lines=[PlayLineIn(main_numbers=[1, 2, 3, 4, 5], special_number=1)],
    )
    with pytest.raises(HTTPException) as exc:
        create_ticket(seeded, user, data)
    assert exc.value.status_code == 404


def test_create_invalid_line_raises_value_error(seeded):
    user = _user(seeded, "d@example.com")
    data = TicketCreate(
        game_key="powerball",
        purchase_date=date(2026, 1, 1),
        lines=[PlayLineIn(main_numbers=[1, 2, 3], special_number=1)],
    )
    with pytest.raises(ValueError):
        create_ticket(seeded, user, data)


# --------------------------------------------------------------------------
# list / get / delete (user scoping)
# --------------------------------------------------------------------------

def _make_ticket(db, user, game_key="powerball"):
    data = TicketCreate(
        game_key=game_key,
        purchase_date=date(2026, 1, 1),
        lines=[PlayLineIn(main_numbers=[1, 2, 3, 4, 5], special_number=10)],
    )
    return create_ticket(db, user, data)


def test_list_user_scoped(seeded):
    alice = _user(seeded, "alice@example.com")
    bob = _user(seeded, "bob@example.com")
    _make_ticket(seeded, alice)
    _make_ticket(seeded, alice)
    _make_ticket(seeded, bob)

    alice_tickets = list_tickets(seeded, alice)
    bob_tickets = list_tickets(seeded, bob)
    assert len(alice_tickets) == 2
    assert len(bob_tickets) == 1
    assert all(t.user_id == alice.id for t in alice_tickets)


def test_list_game_filter(seeded):
    alice = _user(seeded, "alice2@example.com")
    _make_ticket(seeded, alice, game_key="powerball")
    d4 = TicketCreate(
        game_key="daily4",
        purchase_date=date(2026, 1, 1),
        lines=[PlayLineIn(main_numbers=[1, 2, 3, 4], play_type="straight")],
    )
    create_ticket(seeded, alice, d4)

    pb_only = list_tickets(seeded, alice, game_key="powerball")
    assert len(pb_only) == 1


def test_list_status_filter(seeded):
    alice = _user(seeded, "alice3@example.com")
    ticket = _make_ticket(seeded, alice)
    # create a draw + ticket result with status "win"
    draw = Draw(
        game_id=ticket.game_id,
        draw_date=date(2026, 1, 2),
        winning_main=[1, 2, 3, 4, 5],
        winning_special=10,
    )
    seeded.add(draw)
    seeded.flush()
    tr = TicketResult(
        play_line_id=ticket.play_lines[0].id,
        draw_id=draw.id,
        match_main_count=5,
        match_special=True,
        tier_key="5+PB",
        amount_won_cents=5000,
        status="win",
    )
    seeded.add(tr)
    seeded.flush()

    wins = list_tickets(seeded, alice, status="win")
    losses = list_tickets(seeded, alice, status="loss")
    assert len(wins) == 1
    assert len(losses) == 0


def test_get_user_scoped_404_for_other(seeded):
    from fastapi import HTTPException

    alice = _user(seeded, "alice4@example.com")
    bob = _user(seeded, "bob4@example.com")
    ticket = _make_ticket(seeded, alice)

    got = get_ticket(seeded, alice, ticket.id)
    assert got.id == ticket.id

    with pytest.raises(HTTPException) as exc:
        get_ticket(seeded, bob, ticket.id)
    assert exc.value.status_code == 404


def test_get_missing_404(seeded):
    from fastapi import HTTPException

    alice = _user(seeded, "alice5@example.com")
    with pytest.raises(HTTPException) as exc:
        get_ticket(seeded, alice, uuid.uuid4())
    assert exc.value.status_code == 404


def test_delete_user_scoped(seeded):
    from fastapi import HTTPException

    alice = _user(seeded, "alice6@example.com")
    ticket = _make_ticket(seeded, alice)
    delete_ticket(seeded, alice, ticket.id)
    with pytest.raises(HTTPException):
        get_ticket(seeded, alice, ticket.id)


def test_delete_other_user_forbidden(seeded):
    from fastapi import HTTPException

    alice = _user(seeded, "alice7@example.com")
    bob = _user(seeded, "bob7@example.com")
    ticket = _make_ticket(seeded, alice)
    with pytest.raises(HTTPException) as exc:
        delete_ticket(seeded, bob, ticket.id)
    assert exc.value.status_code == 404


def test_to_ticket_out_sums_won(seeded):
    alice = _user(seeded, "alice8@example.com")
    pb = _game(seeded, "powerball")
    ticket = _make_ticket(seeded, alice)
    draw = Draw(
        game_id=ticket.game_id,
        draw_date=date(2026, 1, 2),
        winning_main=[1, 2, 3, 4, 5],
        winning_special=10,
    )
    seeded.add(draw)
    seeded.flush()
    seeded.add(TicketResult(
        play_line_id=ticket.play_lines[0].id,
        draw_id=draw.id,
        amount_won_cents=700,
        status="win",
    ))
    seeded.flush()
    out = to_ticket_out(seeded, ticket, pb)
    assert out.total_won_cents == 700
    assert out.game_key == "powerball"
    assert len(out.lines) == 1
    assert len(out.results) == 1
