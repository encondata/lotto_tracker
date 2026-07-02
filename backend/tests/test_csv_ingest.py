from datetime import date

from sqlalchemy import select

from app.models.draw import Draw, IngestionRun
from app.models.reference import Game
from app.results import csv_ingest
from app.seed import seed_reference_data

# Real TX layout: Name,Month,Day,Year,N1..N5,Powerball,PowerPlay
FAKE_POWERBALL = (
    "Powerball,7,1,2026,5,10,15,20,25,7,3\n"
    "Powerball,6,28,2026,1,2,3,4,5,9,2\n"
)

# Lotto Texas: Name,Month,Day,Year,N1..N6
FAKE_LOTTO = (
    "Lotto Texas,7,1,2026,3,11,22,33,44,54\n"
    "Lotto Texas,6,28,2026,1,2,3,4,5,6\n"
)


def _game(db, key):
    return db.scalar(select(Game).where(Game.key == key))


def test_parse_rows_powerball():
    rows = csv_ingest.parse_rows("powerball", FAKE_POWERBALL)
    assert len(rows) == 2
    r = rows[0]
    assert r["draw_date"] == date(2026, 7, 1)
    assert r["winning_main"] == [5, 10, 15, 20, 25]
    assert r["winning_special"] == 7
    assert r["multiplier"] == 3
    assert r["draw_period"] is None


def test_parse_rows_lotto_texas():
    rows = csv_ingest.parse_rows("lotto_texas", FAKE_LOTTO)
    assert len(rows) == 2
    r = rows[0]
    assert r["draw_date"] == date(2026, 7, 1)
    assert r["winning_main"] == [3, 11, 22, 33, 44, 54]
    assert r["winning_special"] is None


def test_parse_rows_skips_malformed():
    text = FAKE_POWERBALL + "Powerball,bad,row\n" + ",,,,\n"
    rows = csv_ingest.parse_rows("powerball", text)
    assert len(rows) == 2  # malformed rows skipped


def test_ingest_game_inserts_and_writes_run(db_session):
    seed_reference_data(db_session)
    run = csv_ingest.ingest_game(db_session, "powerball", csv_text=FAKE_POWERBALL)
    db_session.flush()
    assert isinstance(run, IngestionRun)
    assert run.status == "success"
    assert run.rows_added == 2

    pb = _game(db_session, "powerball")
    draws = db_session.scalars(
        select(Draw).where(Draw.game_id == pb.id)
    ).all()
    assert len(draws) == 2
    assert all(d.source == "csv" for d in draws)


def test_ingest_game_idempotent(db_session):
    seed_reference_data(db_session)
    csv_ingest.ingest_game(db_session, "powerball", csv_text=FAKE_POWERBALL)
    db_session.flush()
    run2 = csv_ingest.ingest_game(db_session, "powerball", csv_text=FAKE_POWERBALL)
    db_session.flush()
    assert run2.status == "success"
    assert run2.rows_added == 0

    pb = _game(db_session, "powerball")
    draws = db_session.scalars(select(Draw).where(Draw.game_id == pb.id)).all()
    assert len(draws) == 2


def test_ingest_game_fetches_when_no_text(db_session, monkeypatch):
    seed_reference_data(db_session)

    def fake_fetch(url):
        assert url == csv_ingest.GAME_CSV_URLS["powerball"]
        return FAKE_POWERBALL

    monkeypatch.setattr(csv_ingest, "fetch_csv", fake_fetch)
    run = csv_ingest.ingest_game(db_session, "powerball")
    db_session.flush()
    assert run.status == "success"
    assert run.rows_added == 2


def test_ingest_game_failure_records_failed_run(db_session, monkeypatch):
    seed_reference_data(db_session)

    def boom(url):
        raise RuntimeError("network down")

    monkeypatch.setattr(csv_ingest, "fetch_csv", boom)
    run = csv_ingest.ingest_game(db_session, "powerball")
    db_session.flush()
    assert run.status == "failed"
    assert run.errors is not None
