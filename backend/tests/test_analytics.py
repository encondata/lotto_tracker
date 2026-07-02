from datetime import date

import pytest
from sqlalchemy import select

from app.models.draw import Draw, TicketResult
from app.models.reference import Game
from app.models.ticket import PlayLine, Ticket
from app.models.user import User
from app.security import hash_password
from app.seed import seed_reference_data
from app.services import analytics


@pytest.fixture
def seeded(db_session):
    seed_reference_data(db_session)
    return db_session


def _user(db, email):
    u = User(
        email=email,
        password_hash=hash_password("password123"),
        display_name=email.split("@")[0],
        role="user",
    )
    db.add(u)
    db.flush()
    return u


def _game(db, key):
    return db.scalar(select(Game).where(Game.key == key))


def _draw(db, game_id, d):
    draw = Draw(game_id=game_id, draw_date=d, winning_main=[1, 2, 3, 4, 5])
    db.add(draw)
    db.flush()
    return draw


@pytest.fixture
def dataset(seeded):
    """Build a fixed dataset for alice with hand-computable totals.

    T1 powerball 2026-01-10 cost 500: L1 quick-pick WON 700, L2 self NO_WIN
    T2 powerball 2026-02-15 cost 300: L3 self PENDING result
    T3 mega      2026-01-20 cost 500: L4 quick-pick WON 20000, L5 quick-pick NO_WIN
    T4 mega      2026-03-05 cost 500: L6 self, NO result at all (draw not happened)
    """
    db = seeded
    alice = _user(db, "alice@example.com")
    pb = _game(db, "powerball")
    mm = _game(db, "mega_millions")
    dpb = _draw(db, pb.id, date(2026, 1, 9))
    dmm = _draw(db, mm.id, date(2026, 1, 19))

    def line(idx, qp):
        return PlayLine(
            line_index=idx, main_numbers=[1, 2, 3, 4, 5], is_quick_pick=qp
        )

    t1 = Ticket(user_id=alice.id, game_id=pb.id, purchase_date=date(2026, 1, 10),
                total_cost_cents=500, add_ons={},
                play_lines=[line(0, True), line(1, False)])
    t2 = Ticket(user_id=alice.id, game_id=pb.id, purchase_date=date(2026, 2, 15),
                total_cost_cents=300, add_ons={},
                play_lines=[line(0, False)])
    t3 = Ticket(user_id=alice.id, game_id=mm.id, purchase_date=date(2026, 1, 20),
                total_cost_cents=500, add_ons={},
                play_lines=[line(0, True), line(1, True)])
    t4 = Ticket(user_id=alice.id, game_id=mm.id, purchase_date=date(2026, 3, 5),
                total_cost_cents=500, add_ons={},
                play_lines=[line(0, False)])
    db.add_all([t1, t2, t3, t4])
    db.flush()

    def result(line, draw, amount, status):
        db.add(TicketResult(play_line_id=line.id, draw_id=draw.id,
                            amount_won_cents=amount, status=status))

    result(t1.play_lines[0], dpb, 700, "won")
    result(t1.play_lines[1], dpb, 0, "no_win")
    result(t2.play_lines[0], dpb, 0, "pending")
    result(t3.play_lines[0], dmm, 20000, "won")
    result(t3.play_lines[1], dmm, 0, "no_win")
    # t4 line has NO TicketResult
    db.flush()
    return db, alice


def test_summary_totals(dataset):
    db, alice = dataset
    s = analytics.summary(db, alice)
    assert s["total_spent_cents"] == 1800
    assert s["total_won_cents"] == 20700
    assert s["net_cents"] == 18900
    assert s["tickets_purchased"] == 4
    assert s["lines_played"] == 6
    assert s["win_rate"] == pytest.approx(2 / 6)
    assert s["biggest_win_cents"] == 20000
    assert s["roi_pct"] == 1050.0
    assert s["pending_cents"] == 800


def test_summary_empty_user(seeded):
    bob = _user(seeded, "bob@example.com")
    s = analytics.summary(seeded, bob)
    assert s["total_spent_cents"] == 0
    assert s["total_won_cents"] == 0
    assert s["net_cents"] == 0
    assert s["tickets_purchased"] == 0
    assert s["lines_played"] == 0
    assert s["win_rate"] == 0
    assert s["biggest_win_cents"] == 0
    assert s["roi_pct"] == 0
    assert s["pending_cents"] == 0


def test_by_game(dataset):
    db, alice = dataset
    rows = {r["game_key"]: r for r in analytics.by_game(db, alice)}
    assert set(rows) == {"powerball", "mega_millions"}
    pb = rows["powerball"]
    assert pb["display_name"] == "Powerball"
    assert pb["spent_cents"] == 800
    assert pb["won_cents"] == 700
    assert pb["net_cents"] == -100
    assert pb["tickets"] == 2
    mm = rows["mega_millions"]
    assert mm["spent_cents"] == 1000
    assert mm["won_cents"] == 20000
    assert mm["net_cents"] == 19000
    assert mm["tickets"] == 2


def test_over_time_month(dataset):
    db, alice = dataset
    rows = analytics.over_time(db, alice, bucket="month")
    by = {r["period"]: r for r in rows}
    assert [r["period"] for r in rows] == sorted(by)  # ordered
    assert by["2026-01"]["spent_cents"] == 1000
    assert by["2026-01"]["won_cents"] == 20700
    assert by["2026-01"]["net_cents"] == 19700
    assert by["2026-02"]["spent_cents"] == 300
    assert by["2026-02"]["won_cents"] == 0
    assert by["2026-02"]["net_cents"] == -300
    assert by["2026-03"]["spent_cents"] == 500
    assert by["2026-03"]["won_cents"] == 0


def test_over_time_week(dataset):
    db, alice = dataset
    rows = analytics.over_time(db, alice, bucket="week")
    assert all(r["period"].count("-W") == 1 for r in rows)
    # total spent across all weeks equals overall spent
    assert sum(r["spent_cents"] for r in rows) == 1800
    assert sum(r["won_cents"] for r in rows) == 20700


def test_pick_breakdown(dataset):
    db, alice = dataset
    b = analytics.pick_breakdown(db, alice)
    qp = b["quick_pick"]
    assert qp["lines"] == 3
    assert qp["wins"] == 2
    assert qp["win_rate"] == pytest.approx(2 / 3)
    sp = b["self_pick"]
    assert sp["lines"] == 3
    assert sp["wins"] == 0
    assert sp["win_rate"] == 0


def test_date_range_filter(dataset):
    db, alice = dataset
    s = analytics.summary(db, alice, date_from=date(2026, 2, 1))
    # only T2 and T4 (purchased on/after 2026-02-01)
    assert s["total_spent_cents"] == 800
    assert s["total_won_cents"] == 0
    assert s["net_cents"] == -800
    assert s["tickets_purchased"] == 2
    assert s["lines_played"] == 2
    assert s["biggest_win_cents"] == 0
    assert s["roi_pct"] == -100.0
    assert s["pending_cents"] == 800

    rows = analytics.by_game(db, alice, date_from=date(2026, 2, 1))
    assert {r["game_key"] for r in rows} == {"powerball", "mega_millions"}
    assert all(r["won_cents"] == 0 for r in rows)


def test_user_scoping(dataset):
    db, alice = dataset
    bob = _user(db, "bob@example.com")
    pb = _game(db, "powerball")
    t = Ticket(user_id=bob.id, game_id=pb.id, purchase_date=date(2026, 1, 10),
               total_cost_cents=9999, add_ons={},
               play_lines=[PlayLine(line_index=0, main_numbers=[1, 2, 3, 4, 5])])
    db.add(t)
    db.flush()
    # alice's totals unchanged
    s = analytics.summary(db, alice)
    assert s["total_spent_cents"] == 1800
