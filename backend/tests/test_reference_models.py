from app.models.reference import Game, PrizeRule


def test_game_and_prize_rule_persist(db_session):
    game = Game(
        key="powerball", display_name="Powerball", main_count=5,
        main_min=1, main_max=69, has_special_ball=True, special_min=1,
        special_max=26, base_price_cents=200, prize_type="fixed",
        draw_schedule={"days": ["Mon", "Wed", "Sat"], "time": "21:59"},
    )
    db_session.add(game)
    db_session.flush()
    rule = PrizeRule(game_id=game.id, tier_key="match5", match_main=5,
                     match_special=False, base_amount_cents=100_000_000)
    db_session.add(rule)
    db_session.flush()
    assert game.id is not None
    assert rule.game.key == "powerball"
    assert game.prize_rules[0].tier_key == "match5"
