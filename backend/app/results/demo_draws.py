"""Hardcoded recent demo draws so winnings compute without the live scrape.

Dates span late June / early July 2026 across all five games. Pari-mutuel
games (lotto_texas, texas_two_step) carry ``payouts`` dicts so non-fixed tiers
resolve to concrete amounts.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.services.draws import record_draw

# Each entry: kwargs for record_draw (minus db).
DEMO_DRAWS: list[dict] = [
    # Powerball -- Mon/Wed/Sat
    dict(game_key="powerball", draw_date=date(2026, 6, 27),
         winning_main=[8, 15, 27, 42, 60], winning_special=11, multiplier=2),
    dict(game_key="powerball", draw_date=date(2026, 6, 30),
         winning_main=[3, 19, 24, 46, 55], winning_special=7, multiplier=3),
    # Mega Millions -- Tue/Fri
    dict(game_key="mega_millions", draw_date=date(2026, 6, 26),
         winning_main=[5, 12, 33, 44, 68], winning_special=9, multiplier=4),
    dict(game_key="mega_millions", draw_date=date(2026, 6, 30),
         winning_main=[1, 17, 29, 51, 63], winning_special=14, multiplier=2),
    # Lotto Texas -- Mon/Wed/Sat, pari-mutuel payouts (cents)
    dict(game_key="lotto_texas", draw_date=date(2026, 6, 29),
         winning_main=[4, 9, 18, 27, 39, 52],
         payouts={"6": 500000000000, "5": 200000, "4": 5500}),
    dict(game_key="lotto_texas", draw_date=date(2026, 7, 1),
         winning_main=[2, 13, 21, 30, 41, 48],
         payouts={"6": 525000000000, "5": 187500, "4": 4900}),
    # Texas Two Step -- Mon/Thu, pari-mutuel payouts (cents)
    dict(game_key="texas_two_step", draw_date=date(2026, 6, 29),
         winning_main=[6, 14, 22, 31], winning_special=18,
         payouts={"4+B": 20000000000, "4": 150100, "3+B": 5000,
                  "3": 2000, "2+B": 2000}),
    dict(game_key="texas_two_step", draw_date=date(2026, 7, 2),
         winning_main=[3, 11, 25, 34], winning_special=7,
         payouts={"4+B": 22500000000, "4": 148300, "3+B": 5000,
                  "3": 2000, "2+B": 2000}),
    # Daily 4 -- daily, evening period
    dict(game_key="daily4", draw_date=date(2026, 6, 30),
         winning_main=[4, 7, 1, 9], draw_period="evening"),
    dict(game_key="daily4", draw_date=date(2026, 7, 1),
         winning_main=[2, 2, 8, 5], draw_period="evening"),
]


def seed_demo_draws(db: Session) -> None:
    """Record all demo draws. Idempotent (record_draw upserts)."""
    for d in DEMO_DRAWS:
        record_draw(db, **d)
    db.commit()
