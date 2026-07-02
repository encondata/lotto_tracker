"""Orchestrate CSV ingest followed by matching."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.reference import Game
from app.results.csv_ingest import ingest_all
from app.results.matching import match_all_pending


def _summarize(db: Session, runs) -> list[dict]:
    # Map game_id -> key for readable summaries.
    keys = {g.id: g.key for g in db.scalars(select(Game)).all()}
    summaries = []
    for run in runs:
        summaries.append({
            "game_key": keys.get(run.game_id),
            "status": run.status,
            "rows_added": run.rows_added,
            "errors": run.errors,
        })
    return summaries


def run_pipeline(db: Session) -> dict:
    """Ingest all games (best-effort) then match all tickets."""
    runs = ingest_all(db)
    results_created = match_all_pending(db)
    return {
        "ingestion": _summarize(db, runs),
        "results_created": results_created,
    }
