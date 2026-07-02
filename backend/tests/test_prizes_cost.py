from sqlalchemy import select

from app.models.reference import Game
from app.models.ticket import PlayLine
from app.prizes.cost import ticket_cost_cents
from app.seed import seed_reference_data


def _game(db_session, key):
    return db_session.scalar(select(Game).where(Game.key == key))


def _line(main, special=None, play_type=None, wager_cents=0):
    return PlayLine(
        line_index=0,
        main_numbers=main,
        special_number=special,
        play_type=play_type,
        wager_cents=wager_cents,
    )


def test_powerball_base_cost(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    lines = [_line([1, 2, 3, 4, 5], special=6) for _ in range(3)]
    cost = ticket_cost_cents(pb, lines, add_ons={}, num_draws=1)
    assert cost == 200 * 3  # 600


def test_powerball_power_play_and_draws(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    lines = [_line([1, 2, 3, 4, 5], special=6) for _ in range(3)]
    cost = ticket_cost_cents(pb, lines, add_ons={"power_play": True}, num_draws=2)
    # (200 + 100) * 3 lines * 2 draws = 1800
    assert cost == 1800


def test_mega_no_separate_addon(db_session):
    seed_reference_data(db_session)
    mm = _game(db_session, "mega_millions")
    lines = [_line([1, 2, 3, 4, 5], special=6) for _ in range(2)]
    cost = ticket_cost_cents(mm, lines, add_ons={}, num_draws=1)
    assert cost == 500 * 2


def test_lotto_extra(db_session):
    seed_reference_data(db_session)
    lt = _game(db_session, "lotto_texas")
    lines = [_line([1, 2, 3, 4, 5, 6]) for _ in range(2)]
    cost = ticket_cost_cents(lt, lines, add_ons={"extra": True}, num_draws=1)
    # (100 + 100) * 2 = 400
    assert cost == 400


def test_daily4_wager_lines(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    lines = [_line([1, 2, 3, 4], play_type="straight", wager_cents=50),
             _line([5, 6, 7, 8], play_type="straight", wager_cents=100)]
    cost = ticket_cost_cents(d4, lines, add_ons={}, num_draws=1)
    assert cost == 150  # 50 + 100


def test_daily4_fireball_doubles(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    lines = [_line([1, 2, 3, 4], play_type="straight", wager_cents=100)]
    cost = ticket_cost_cents(d4, lines, add_ons={"fireball": True}, num_draws=1)
    assert cost == 200  # 100 * 2


def test_daily4_wager_defaults_to_base_price(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    lines = [_line([1, 2, 3, 4], play_type="straight", wager_cents=0)]
    cost = ticket_cost_cents(d4, lines, add_ons={}, num_draws=1)
    assert cost == 100  # defaults to base_price_cents


def test_daily4_fireball_with_draws(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    lines = [_line([1, 2, 3, 4], play_type="straight", wager_cents=100)]
    cost = ticket_cost_cents(d4, lines, add_ons={"fireball": True}, num_draws=3)
    assert cost == 600  # 100 * 2 * 3
