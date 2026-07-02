"""Ingest official Texas Lottery winning-number CSVs into Draw rows.

The TX CSVs have no header and one draw per line. Column layout is roughly::

    GameName,Month,Day,Year,N1..Nk[,special][,multiplier]

Per-game column mapping is applied in :func:`parse_rows`. All network access is
isolated in :func:`fetch_csv` so tests can monkeypatch it and never hit the wire.
"""

from __future__ import annotations

import csv
import io
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.draw import Draw, IngestionRun
from app.models.reference import Game

# Official Texas Lottery winning-number CSV exports. mega_millions /
# texas_two_step / daily4 URLs are best-effort and may 404 -- that is fine.
GAME_CSV_URLS: dict[str, str] = {
    "powerball": "https://www.texaslottery.com/export/sites/lottery/Games/Powerball/Winning_Numbers/powerball.csv",
    "lotto_texas": "https://www.texaslottery.com/export/sites/lottery/Games/Lotto_Texas/Winning_Numbers/lottotexas.csv",
    "mega_millions": "https://www.texaslottery.com/export/sites/lottery/Games/Mega_Millions/Winning_Numbers/megamillions.csv",
    "texas_two_step": "https://www.texaslottery.com/export/sites/lottery/Games/Texas_Two_Step/Winning_Numbers/twostep.csv",
    "daily4": "https://www.texaslottery.com/export/sites/lottery/Games/Daily_4/Winning_Numbers/daily4.csv",
}

# How many leading columns before the numbers: Name, Month, Day, Year.
_DATE_COLS = 4


def fetch_csv(url: str) -> str:
    """Fetch CSV text over HTTP. The ONLY network call in this module."""
    resp = httpx.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _ints(values: list[str]) -> list[int]:
    return [int(v.strip()) for v in values]


def _row_date(cols: list[str]) -> date:
    month, day, year = int(cols[1]), int(cols[2]), int(cols[3])
    return date(year, month, day)


def _parse_powerball(cols: list[str]) -> dict:
    nums = _ints(cols[_DATE_COLS:_DATE_COLS + 5])
    special = int(cols[_DATE_COLS + 5])
    multiplier = None
    if len(cols) > _DATE_COLS + 6 and cols[_DATE_COLS + 6].strip():
        multiplier = int(cols[_DATE_COLS + 6])
    return dict(winning_main=nums, winning_special=special,
                multiplier=multiplier, draw_period=None)


def _parse_lotto_texas(cols: list[str]) -> dict:
    nums = _ints(cols[_DATE_COLS:_DATE_COLS + 6])
    return dict(winning_main=nums, winning_special=None,
                multiplier=None, draw_period=None)


def _parse_mega_millions(cols: list[str]) -> dict:
    nums = _ints(cols[_DATE_COLS:_DATE_COLS + 5])
    special = int(cols[_DATE_COLS + 5])
    multiplier = None
    if len(cols) > _DATE_COLS + 6 and cols[_DATE_COLS + 6].strip():
        multiplier = int(cols[_DATE_COLS + 6])
    return dict(winning_main=nums, winning_special=special,
                multiplier=multiplier, draw_period=None)


def _parse_texas_two_step(cols: list[str]) -> dict:
    nums = _ints(cols[_DATE_COLS:_DATE_COLS + 4])
    bonus = int(cols[_DATE_COLS + 4])
    return dict(winning_main=nums, winning_special=bonus,
                multiplier=None, draw_period=None)


def _parse_daily4(cols: list[str]) -> dict:
    digits = _ints(cols[_DATE_COLS:_DATE_COLS + 4])
    # Optional trailing period / fireball columns; treat non-numeric trailing
    # token as the draw period, else leave period None.
    draw_period = None
    tail = cols[_DATE_COLS + 4:]
    for tok in tail:
        tok = tok.strip()
        if tok and not tok.isdigit():
            draw_period = tok.lower()
            break
    return dict(winning_main=digits, winning_special=None,
                multiplier=None, draw_period=draw_period)


_PARSERS = {
    "powerball": _parse_powerball,
    "lotto_texas": _parse_lotto_texas,
    "mega_millions": _parse_mega_millions,
    "texas_two_step": _parse_texas_two_step,
    "daily4": _parse_daily4,
}

# Minimum column count required (date cols + minimum number columns).
_MIN_COLS = {
    "powerball": _DATE_COLS + 6,
    "lotto_texas": _DATE_COLS + 6,
    "mega_millions": _DATE_COLS + 6,
    "texas_two_step": _DATE_COLS + 5,
    "daily4": _DATE_COLS + 4,
}


def parse_rows(game_key: str, csv_text: str) -> list[dict]:
    """Parse CSV text into a list of draw dicts. Malformed rows are skipped."""
    parser = _PARSERS[game_key]
    min_cols = _MIN_COLS[game_key]
    rows: list[dict] = []
    reader = csv.reader(io.StringIO(csv_text))
    for cols in reader:
        if not cols or len(cols) < min_cols:
            continue
        try:
            row = {"draw_date": _row_date(cols)}
            row.update(parser(cols))
            rows.append(row)
        except (ValueError, IndexError):
            continue
    return rows


def _get_game(db: Session, game_key: str) -> Game:
    game = db.scalar(select(Game).where(Game.key == game_key))
    if game is None:
        raise ValueError(f"Unknown game '{game_key}'")
    return game


def _draw_exists(db: Session, game_id, draw_date, draw_period) -> bool:
    stmt = select(Draw.id).where(
        Draw.game_id == game_id,
        Draw.draw_date == draw_date,
    )
    if draw_period is None:
        stmt = stmt.where(Draw.draw_period.is_(None))
    else:
        stmt = stmt.where(Draw.draw_period == draw_period)
    return db.scalar(stmt) is not None


def ingest_game(db: Session, game_key: str, csv_text: str | None = None) -> IngestionRun:
    """Ingest one game's CSV, upserting draws. Never raises: failures are
    captured on the returned IngestionRun."""
    try:
        game = _get_game(db, game_key)
        if csv_text is None:
            csv_text = fetch_csv(GAME_CSV_URLS[game_key])
        rows = parse_rows(game_key, csv_text)

        added = 0
        for r in rows:
            if _draw_exists(db, game.id, r["draw_date"], r["draw_period"]):
                continue
            db.add(Draw(
                game_id=game.id,
                draw_date=r["draw_date"],
                draw_period=r["draw_period"],
                winning_main=r["winning_main"],
                winning_special=r["winning_special"],
                multiplier=r["multiplier"],
                source="csv",
            ))
            added += 1
        db.flush()

        run = IngestionRun(
            game_id=game.id, status="success", rows_added=added, errors=None,
        )
        db.add(run)
        db.flush()
        return run
    except Exception as exc:  # noqa: BLE001 - best-effort, capture on the run
        game_id = None
        try:
            game_id = _get_game(db, game_key).id
        except Exception:
            pass
        run = IngestionRun(
            game_id=game_id, status="failed", rows_added=0,
            errors=f"{type(exc).__name__}: {exc}",
        )
        if game_id is not None:
            db.add(run)
            db.flush()
        return run


def ingest_all(db: Session) -> list[IngestionRun]:
    """Best-effort ingest of every known game."""
    runs: list[IngestionRun] = []
    for game_key in GAME_CSV_URLS:
        runs.append(ingest_game(db, game_key))
    return runs
