"""Populate the app database with a rich demo dataset.

Idempotent: ensures demo users + reference data + demo draws, then (only if the
demo user has no tickets yet) creates a spread of tickets designed to produce a
mix of wins, losses, and a pending ("money in play") ticket against the seeded
demo draws, and runs matching so results/analytics are populated.

Run against the app DB:
    DATABASE_URL=postgresql+psycopg://lotto:lotto@localhost:5433/lotto \
        python -m app.demo
"""
from datetime import date

from sqlalchemy import select

from app.bootstrap import ensure_demo_users
from app.db import SessionLocal
from app.models.ticket import Ticket
from app.models.user import User
from app.results.demo_draws import seed_demo_draws
from app.results.matching import match_all_pending
from app.schemas.ticket import PlayLineIn, TicketCreate
from app.seed import seed_reference_data
from app.services.tickets import create_ticket

DEMO_EMAIL = "demo@lottotracker.io"

# Tickets crafted against seeded demo draws:
#   powerball 2026-06-30 -> [3,19,24,46,55] PB 7 (x3)
#   mega_millions 2026-06-30 -> [1,17,29,51,63] MB 14 (x2)
#   lotto_texas 2026-07-01 -> [2,13,21,30,41,48] (+payouts)
#   daily4 2026-07-01 evening -> [2,2,8,5]
#   texas_two_step 2026-06-29 -> [6,14,22,31] B 18 (+payouts)
DEMO_TICKETS: list[TicketCreate] = [
    # Powerball: line A hits 4 mains + PB (big win, x3 power play); line B hits 3 mains.
    TicketCreate(
        game_key="powerball", purchase_date=date(2026, 6, 30), num_draws=1,
        add_ons={"power_play": True}, entry_method="manual",
        lines=[
            PlayLineIn(main_numbers=[3, 19, 24, 46, 11], special_number=7, is_quick_pick=False),
            PlayLineIn(main_numbers=[3, 19, 24, 60, 61], special_number=12, is_quick_pick=True),
        ],
    ),
    # Powerball loser (no matches).
    TicketCreate(
        game_key="powerball", purchase_date=date(2026, 6, 30), num_draws=1,
        add_ons={}, entry_method="manual",
        lines=[PlayLineIn(main_numbers=[1, 2, 4, 5, 6], special_number=1, is_quick_pick=True)],
    ),
    # Mega Millions: 3 mains + MB (built-in x2 multiplier).
    TicketCreate(
        game_key="mega_millions", purchase_date=date(2026, 6, 30), num_draws=1,
        add_ons={}, entry_method="ocr",
        lines=[PlayLineIn(main_numbers=[1, 17, 29, 7, 8], special_number=14, is_quick_pick=False)],
    ),
    # Lotto Texas: 4 of 6 -> pari-mutuel payout from the draw.
    TicketCreate(
        game_key="lotto_texas", purchase_date=date(2026, 7, 1), num_draws=1,
        add_ons={"extra": True}, entry_method="manual",
        lines=[PlayLineIn(main_numbers=[2, 13, 21, 30, 7, 8], is_quick_pick=False)],
    ),
    # Daily 4 straight: exact match of the evening draw -> $5,000.
    TicketCreate(
        game_key="daily4", purchase_date=date(2026, 7, 1), num_draws=1,
        add_ons={}, entry_method="manual",
        lines=[PlayLineIn(main_numbers=[2, 2, 8, 5], play_type="straight", wager_cents=100)],
    ),
    # Texas Two Step: 3 mains + bonus (pari-mutuel).
    TicketCreate(
        game_key="texas_two_step", purchase_date=date(2026, 6, 29), num_draws=1,
        add_ons={}, entry_method="manual",
        lines=[PlayLineIn(main_numbers=[6, 14, 22, 9], special_number=18, is_quick_pick=True)],
    ),
    # Pending: bought for a future date with no draw yet -> "money in play".
    TicketCreate(
        game_key="texas_two_step", purchase_date=date(2026, 7, 20), num_draws=2,
        add_ons={}, entry_method="manual",
        lines=[PlayLineIn(main_numbers=[1, 2, 3, 4], special_number=5, is_quick_pick=True)],
    ),
]


def seed_demo(db) -> dict:
    ensure_demo_users(db)
    seed_reference_data(db)
    seed_demo_draws(db)
    db.commit()

    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    existing = db.scalar(select(Ticket).where(Ticket.user_id == user.id))
    created = 0
    if existing is None:
        for data in DEMO_TICKETS:
            create_ticket(db, user, data)
            created += 1
        db.commit()

    results = match_all_pending(db)
    db.commit()
    return {"tickets_created": created, "results_created": results}


if __name__ == "__main__":
    with SessionLocal() as s:
        summary = seed_demo(s)
        print(f"Demo seeded: {summary}")
