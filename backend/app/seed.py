from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.reference import Game, PrizeRule

GAMES = [
    dict(key="powerball", display_name="Powerball", main_count=5, main_min=1,
         main_max=69, has_special_ball=True, special_min=1, special_max=26,
         base_price_cents=200, prize_type="fixed",
         draw_schedule={"days": ["Mon", "Wed", "Sat"], "time": "21:59"}),
    dict(key="mega_millions", display_name="Mega Millions", main_count=5, main_min=1,
         main_max=70, has_special_ball=True, special_min=1, special_max=24,
         base_price_cents=500, prize_type="fixed",
         draw_schedule={"days": ["Tue", "Fri"], "time": "21:59"}),
    dict(key="lotto_texas", display_name="Lotto Texas", main_count=6, main_min=1,
         main_max=54, has_special_ball=False, base_price_cents=100,
         prize_type="pari_mutuel",
         draw_schedule={"days": ["Mon", "Wed", "Sat"], "time": "22:12"}),
    dict(key="texas_two_step", display_name="Texas Two Step", main_count=4, main_min=1,
         main_max=35, has_special_ball=True, special_min=1, special_max=35,
         base_price_cents=100, prize_type="mixed",
         draw_schedule={"days": ["Mon", "Thu"], "time": "22:12"}),
    dict(key="daily4", display_name="Daily 4", main_count=4, main_min=0, main_max=9,
         has_special_ball=False, base_price_cents=100, prize_type="fixed",
         draw_schedule={"days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                        "periods": {"morning": "10:00", "day": "12:27",
                                    "evening": "18:00", "night": "22:12"}}),
]

# tier_key, match_main, match_special, play_type, base_amount_cents
# Amounts are $1-wager base amounts in cents. Pari-mutuel tiers -> None.
PRIZE_RULES = {
    "powerball": [
        ("5+PB", 5, True, None, None),        # jackpot
        ("5", 5, False, None, 100_000_000),
        ("4+PB", 4, True, None, 5_000_000),
        ("4", 4, False, None, 10_000),
        ("3+PB", 3, True, None, 10_000),
        ("3", 3, False, None, 700),
        ("2+PB", 2, True, None, 700),
        ("1+PB", 1, True, None, 400),
        ("0+PB", 0, True, None, 400),
    ],
    "mega_millions": [
        ("5+MB", 5, True, None, None),         # jackpot
        ("5", 5, False, None, 100_000_000),
        ("4+MB", 4, True, None, 1_000_000),
        ("4", 4, False, None, 50_000),
        ("3+MB", 3, True, None, 20_000),
        ("3", 3, False, None, 1_000),
        ("2+MB", 2, True, None, 1_000),
        ("1+MB", 1, True, None, 400),
        ("0+MB", 0, True, None, 200),
    ],
    "lotto_texas": [
        ("6", 6, False, None, None),           # jackpot, pari-mutuel
        ("5", 5, False, None, None),           # pari-mutuel
        ("4", 4, False, None, None),           # pari-mutuel
        ("3", 3, False, None, 300),            # fixed $3
    ],
    "texas_two_step": [
        ("4+B", 4, True, None, None),          # jackpot, pari-mutuel
        ("4", 4, False, None, None),           # pari-mutuel (~$1,501)
        ("3+B", 3, True, None, None),          # pari-mutuel (~$50)
        ("3", 3, False, None, None),           # pari-mutuel (~$20)
        ("2+B", 2, True, None, None),          # pari-mutuel (~$20)
        ("1+B", 1, True, None, 700),           # fixed $7
        ("0+B", 0, True, None, 500),           # fixed $5
    ],
    # Daily 4 base ($1 wager) fixed amounts; Fireball handled in prize engine (Plan 3).
    "daily4": [
        ("straight", 4, False, "straight", 500_000),
        ("box-4", 4, False, "box-4", 120_000),
        ("box-6", 4, False, "box-6", 80_000),
        ("box-12", 4, False, "box-12", 40_000),
        ("box-24", 4, False, "box-24", 20_000),
        ("pair-front", 2, False, "pair-front", 5_000),
        ("pair-mid", 2, False, "pair-mid", 5_000),
        ("pair-back", 2, False, "pair-back", 5_000),
    ],
}


def seed_reference_data(session: Session) -> None:
    for g in GAMES:
        existing = session.scalar(select(Game).where(Game.key == g["key"]))
        if existing:
            for k, v in g.items():
                setattr(existing, k, v)
            game = existing
        else:
            game = Game(**g)
            session.add(game)
        session.flush()
        for tier_key, mm, ms, pt, amt in PRIZE_RULES[g["key"]]:
            rule = session.scalar(
                select(PrizeRule).where(
                    PrizeRule.game_id == game.id,
                    PrizeRule.tier_key == tier_key,
                    PrizeRule.play_type.is_(pt) if pt is None else PrizeRule.play_type == pt,
                )
            )
            if rule is None:
                rule = PrizeRule(game_id=game.id, tier_key=tier_key)
                session.add(rule)
            rule.match_main = mm
            rule.match_special = ms
            rule.play_type = pt
            rule.base_amount_cents = amt
    session.commit()


if __name__ == "__main__":
    with SessionLocal() as s:
        seed_reference_data(s)
        print("Seeded reference data.")
