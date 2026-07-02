from datetime import date

from sqlalchemy import select

from app.models.reference import Game
from app.models.draw import Draw
from app.models.ticket import PlayLine
from app.prizes.engine import compute_win, WinResult
from app.seed import seed_reference_data


def _game(db_session, key):
    return db_session.scalar(select(Game).where(Game.key == key))


def _draw(game, main, special=None, multiplier=None, payouts=None):
    return Draw(
        game_id=game.id,
        draw_date=date(2026, 7, 1),
        winning_main=main,
        winning_special=special,
        multiplier=multiplier,
        payouts=payouts,
    )


def _line(main, special=None, play_type=None, wager_cents=100):
    return PlayLine(
        line_index=0,
        main_numbers=main,
        special_number=special,
        play_type=play_type,
        wager_cents=wager_cents,
    )


# ---------- Powerball ----------
def test_pb_jackpot_pending_when_no_payouts(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 3, 4, 5], special=10)
    line = _line([1, 2, 3, 4, 5], special=10)
    res = compute_win(db_session, pb, line, draw, add_ons={})
    assert isinstance(res, WinResult)
    assert res.tier_key == "5+PB"
    assert res.status == "won"
    assert res.amount_pending is True
    assert res.amount_cents == 0


def test_pb_jackpot_not_multiplied(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 3, 4, 5], special=10, multiplier=10,
                 payouts={"5+PB": 90_000_000_000})
    line = _line([1, 2, 3, 4, 5], special=10)
    res = compute_win(db_session, pb, line, draw, add_ons={"power_play": True})
    assert res.amount_cents == 90_000_000_000
    assert res.amount_pending is False


def test_pb_match5_power_play_cap(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 3, 4, 5], special=99, multiplier=5)
    line = _line([1, 2, 3, 4, 5], special=10)  # 5 main, no PB
    res = compute_win(db_session, pb, line, draw, add_ons={"power_play": True})
    assert res.tier_key == "5"
    # base 100_000_000 * 5 = 500_000_000 but capped at 200_000_000
    assert res.amount_cents == 200_000_000


def test_pb_match4_power_play_multiplies(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 3, 4, 50], special=99, multiplier=5)
    line = _line([1, 2, 3, 4, 60], special=10)  # 4 main, no PB -> "4" base 10_000
    res = compute_win(db_session, pb, line, draw, add_ons={"power_play": True})
    assert res.tier_key == "4"
    assert res.amount_cents == 50_000  # 10_000 * 5


def test_pb_match3_no_special(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 3, 40, 50], special=10)
    line = _line([1, 2, 3, 60, 61], special=99)
    res = compute_win(db_session, pb, line, draw, add_ons={})
    assert res.tier_key == "3"
    assert res.amount_cents == 700
    assert res.status == "won"


def test_pb_2_no_special_no_win(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 30, 40, 50], special=10)
    line = _line([1, 2, 60, 61, 62], special=99)
    res = compute_win(db_session, pb, line, draw, add_ons={})
    assert res.status == "no_win"
    assert res.tier_key is None
    assert res.amount_cents == 0


def test_pb_no_power_play_no_multiply(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 3, 4, 50], special=99, multiplier=5)
    line = _line([1, 2, 3, 4, 60], special=10)
    res = compute_win(db_session, pb, line, draw, add_ons={})
    assert res.amount_cents == 10_000  # no power play, no multiply


# ---------- Mega Millions ----------
def test_mega_builtin_multiplier(db_session):
    seed_reference_data(db_session)
    mm = _game(db_session, "mega_millions")
    draw = _draw(mm, [1, 2, 3, 4, 50], special=7, multiplier=4)
    line = _line([1, 2, 3, 4, 60], special=7)  # 4+MB base 1_000_000
    res = compute_win(db_session, mm, line, draw, add_ons={})
    assert res.tier_key == "4+MB"
    assert res.amount_cents == 4_000_000  # 1_000_000 * 4


def test_mega_multiplier_default_1(db_session):
    seed_reference_data(db_session)
    mm = _game(db_session, "mega_millions")
    draw = _draw(mm, [1, 2, 3, 4, 50], special=7, multiplier=None)
    line = _line([1, 2, 3, 4, 60], special=7)
    res = compute_win(db_session, mm, line, draw, add_ons={})
    assert res.amount_cents == 1_000_000


def test_mega_jackpot_not_multiplied(db_session):
    seed_reference_data(db_session)
    mm = _game(db_session, "mega_millions")
    draw = _draw(mm, [1, 2, 3, 4, 5], special=7, multiplier=4,
                 payouts={"5+MB": 50_000_000_000})
    line = _line([1, 2, 3, 4, 5], special=7)
    res = compute_win(db_session, mm, line, draw, add_ons={})
    assert res.amount_cents == 50_000_000_000


# ---------- Lotto Texas (pari-mutuel) ----------
def test_lotto_match5_with_payouts(db_session):
    seed_reference_data(db_session)
    lt = _game(db_session, "lotto_texas")
    draw = _draw(lt, [1, 2, 3, 4, 5, 6], payouts={"5": 200_000})
    line = _line([1, 2, 3, 4, 5, 40])
    res = compute_win(db_session, lt, line, draw, add_ons={})
    assert res.tier_key == "5"
    assert res.amount_cents == 200_000
    assert res.amount_pending is False


def test_lotto_match5_pending_no_payouts(db_session):
    seed_reference_data(db_session)
    lt = _game(db_session, "lotto_texas")
    draw = _draw(lt, [1, 2, 3, 4, 5, 6])
    line = _line([1, 2, 3, 4, 5, 40])
    res = compute_win(db_session, lt, line, draw, add_ons={})
    assert res.tier_key == "5"
    assert res.amount_pending is True
    assert res.amount_cents == 0
    assert res.status == "won"


def test_lotto_match3_fixed(db_session):
    seed_reference_data(db_session)
    lt = _game(db_session, "lotto_texas")
    draw = _draw(lt, [1, 2, 3, 40, 50, 51])
    line = _line([1, 2, 3, 60, 61, 62])
    res = compute_win(db_session, lt, line, draw, add_ons={})
    assert res.tier_key == "3"
    assert res.amount_cents == 300


def test_lotto_match3_extra(db_session):
    seed_reference_data(db_session)
    lt = _game(db_session, "lotto_texas")
    draw = _draw(lt, [1, 2, 3, 40, 50, 51])
    line = _line([1, 2, 3, 60, 61, 62])
    res = compute_win(db_session, lt, line, draw, add_ons={"extra": True})
    assert res.tier_key == "3"
    assert res.amount_cents == 1_300  # 300 + 1000


# ---------- Texas Two Step ----------
def test_tts_1_plus_b_fixed(db_session):
    seed_reference_data(db_session)
    tts = _game(db_session, "texas_two_step")
    draw = _draw(tts, [1, 20, 21, 22], special=7)
    line = _line([1, 30, 31, 32], special=7)
    res = compute_win(db_session, tts, line, draw, add_ons={})
    assert res.tier_key == "1+B"
    assert res.amount_cents == 700


def test_tts_4_plus_b_pending(db_session):
    seed_reference_data(db_session)
    tts = _game(db_session, "texas_two_step")
    draw = _draw(tts, [1, 2, 3, 4], special=7)
    line = _line([1, 2, 3, 4], special=7)
    res = compute_win(db_session, tts, line, draw, add_ons={})
    assert res.tier_key == "4+B"
    assert res.amount_pending is True
    assert res.amount_cents == 0


# ---------- Daily 4 ----------
def test_daily4_straight_full_wager(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [1, 2, 3, 4])
    line = _line([1, 2, 3, 4], play_type="straight", wager_cents=100)
    res = compute_win(db_session, d4, line, draw, add_ons={})
    assert res.tier_key == "straight"
    assert res.amount_cents == 500_000


def test_daily4_straight_half_wager(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [1, 2, 3, 4])
    line = _line([1, 2, 3, 4], play_type="straight", wager_cents=50)
    res = compute_win(db_session, d4, line, draw, add_ons={})
    assert res.amount_cents == 250_000


def test_daily4_box_24(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [4, 3, 2, 1])
    line = _line([1, 2, 3, 4], play_type="box", wager_cents=100)
    res = compute_win(db_session, d4, line, draw, add_ons={})
    assert res.tier_key == "box-24"
    assert res.amount_cents == 20_000


def test_daily4_pair_front(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [1, 2, 9, 9])
    line = _line([1, 2, 0, 0], play_type="pair-front", wager_cents=100)
    res = compute_win(db_session, d4, line, draw, add_ons={})
    assert res.tier_key == "pair-front"
    assert res.amount_cents == 5_000


def test_daily4_fireball_returns_normal(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [1, 2, 3, 4])
    line = _line([1, 2, 3, 4], play_type="straight", wager_cents=100)
    res = compute_win(db_session, d4, line, draw, add_ons={"fireball": True})
    assert res.tier_key == "straight"
    assert res.amount_cents == 500_000
