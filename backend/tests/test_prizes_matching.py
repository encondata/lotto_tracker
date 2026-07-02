from sqlalchemy import select

from app.models.reference import Game
from app.models.draw import Draw
from app.models.ticket import PlayLine
from app.prizes.matching import match_line, MatchResult
from app.seed import seed_reference_data


def _game(db_session, key):
    return db_session.scalar(select(Game).where(Game.key == key))


def _draw(game, main, special=None, multiplier=None, payouts=None):
    return Draw(
        game_id=game.id,
        draw_date=__import__("datetime").date(2026, 7, 1),
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


def test_powerball_5_plus_pb(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 3, 4, 5], special=10)
    line = _line([1, 2, 3, 4, 5], special=10)
    res = match_line(pb, line, draw)
    assert isinstance(res, MatchResult)
    assert res.match_main == 5
    assert res.match_special is True
    assert res.tier_key == "5+PB"


def test_powerball_3_no_special(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 3, 40, 50], special=10)
    line = _line([1, 2, 3, 60, 61], special=99)
    res = match_line(pb, line, draw)
    assert res.match_main == 3
    assert res.match_special is False
    assert res.tier_key == "3"


def test_powerball_2_no_special_is_no_win(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 30, 40, 50], special=10)
    line = _line([1, 2, 60, 61, 62], special=99)
    res = match_line(pb, line, draw)
    assert res.match_main == 2
    assert res.match_special is False
    assert res.tier_key is None


def test_powerball_2_plus_pb_wins(db_session):
    seed_reference_data(db_session)
    pb = _game(db_session, "powerball")
    draw = _draw(pb, [1, 2, 30, 40, 50], special=10)
    line = _line([1, 2, 60, 61, 62], special=10)
    res = match_line(pb, line, draw)
    assert res.tier_key == "2+PB"


def test_lotto_texas_match_5(db_session):
    seed_reference_data(db_session)
    lt = _game(db_session, "lotto_texas")
    draw = _draw(lt, [1, 2, 3, 4, 5, 6])
    line = _line([1, 2, 3, 4, 5, 40])
    res = match_line(lt, line, draw)
    assert res.match_main == 5
    assert res.match_special is False
    assert res.tier_key == "5"


def test_texas_two_step_1_plus_b(db_session):
    seed_reference_data(db_session)
    tts = _game(db_session, "texas_two_step")
    draw = _draw(tts, [1, 20, 21, 22], special=7)
    line = _line([1, 30, 31, 32], special=7)
    res = match_line(tts, line, draw)
    assert res.match_main == 1
    assert res.match_special is True
    assert res.tier_key == "1+B"


def test_daily4_straight_exact(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [1, 2, 3, 4])
    line = _line([1, 2, 3, 4], play_type="straight")
    res = match_line(d4, line, draw)
    assert res.tier_key == "straight"


def test_daily4_straight_no_match(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [1, 2, 3, 4])
    line = _line([4, 3, 2, 1], play_type="straight")
    res = match_line(d4, line, draw)
    assert res.tier_key is None


def test_daily4_box_24_all_distinct(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [4, 3, 2, 1])
    line = _line([1, 2, 3, 4], play_type="box")
    res = match_line(d4, line, draw)
    assert res.tier_key == "box-24"


def test_daily4_box_12_one_pair(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [2, 1, 3, 1])
    line = _line([1, 1, 2, 3], play_type="box")
    res = match_line(d4, line, draw)
    assert res.tier_key == "box-12"


def test_daily4_pair_front(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [1, 2, 9, 9])
    line = _line([1, 2, 0, 0], play_type="pair-front")
    res = match_line(d4, line, draw)
    assert res.tier_key == "pair-front"


def test_daily4_pair_back(db_session):
    seed_reference_data(db_session)
    d4 = _game(db_session, "daily4")
    draw = _draw(d4, [9, 9, 3, 4])
    line = _line([0, 0, 3, 4], play_type="pair-back")
    res = match_line(d4, line, draw)
    assert res.tier_key == "pair-back"
