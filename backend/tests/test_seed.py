from sqlalchemy import select

from app.models.reference import Game, PrizeRule
from app.seed import seed_reference_data


def test_seed_creates_five_games(db_session):
    seed_reference_data(db_session)
    keys = set(db_session.scalars(select(Game.key)).all())
    assert keys == {"powerball", "mega_millions", "lotto_texas",
                    "texas_two_step", "daily4"}


def test_seed_powerball_rules_and_ranges(db_session):
    seed_reference_data(db_session)
    pb = db_session.scalar(select(Game).where(Game.key == "powerball"))
    assert (pb.main_max, pb.special_max, pb.base_price_cents) == (69, 26, 200)
    match5 = db_session.scalar(
        select(PrizeRule).where(PrizeRule.game_id == pb.id, PrizeRule.tier_key == "5"))
    assert match5.base_amount_cents == 100_000_000  # $1,000,000


def test_seed_is_idempotent(db_session):
    seed_reference_data(db_session)
    seed_reference_data(db_session)
    assert len(db_session.scalars(select(Game)).all()) == 5
