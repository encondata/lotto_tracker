"""Analytics aggregations for a user's lottery activity.

All figures are scoped to the current user's tickets. Money is integer cents.

Definitions
-----------
Spent   : sum of Ticket.total_cost_cents for the user's tickets (optionally within
          a purchase_date range).
Won     : sum of TicketResult.amount_won_cents for results whose play_line belongs
          to the user's tickets and status == 'won'.
Net     : won - spent.
Pending ("money in play"): sum of Ticket.total_cost_cents for tickets that are not
          fully settled. A ticket counts as pending if it has at least one play_line
          with a TicketResult status == 'pending', OR at least one play_line with no
          TicketResult at all (its draw has not been matched yet). Tickets whose every
          play_line has only settled results ('won'/'no_win') are excluded.
Win rate: winning lines / total lines. A line "wins" if it has any TicketResult with
          status == 'won'. 0 when there are no lines.
ROI %   : net / spent * 100, rounded to 1 decimal. 0 when spent == 0.

Joins go PlayLine.ticket_id -> Ticket.id and TicketResult.play_line_id -> PlayLine.id;
there is no direct ticket_id on TicketResult.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.draw import TicketResult
from app.models.reference import Game
from app.models.ticket import PlayLine, Ticket
from app.models.user import User


def _ticket_filter(user: User, date_from: date | None, date_to: date | None):
    conds = [Ticket.user_id == user.id]
    if date_from is not None:
        conds.append(Ticket.purchase_date >= date_from)
    if date_to is not None:
        conds.append(Ticket.purchase_date <= date_to)
    return conds


def summary(
    db: Session,
    user: User,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    tf = _ticket_filter(user, date_from, date_to)

    # Spent + ticket count (no join, so ticket cost is not fanned out by play_lines).
    spent_stmt = (
        select(
            func.coalesce(func.sum(Ticket.total_cost_cents), 0),
            func.count(Ticket.id),
        )
        .select_from(Ticket)
        .where(*tf)
    )
    total_spent, tickets_purchased = db.execute(spent_stmt).one()

    # Lines played = count of play_lines across the user's tickets.
    lines_played = db.scalar(
        select(func.count(PlayLine.id))
        .select_from(PlayLine)
        .join(Ticket, Ticket.id == PlayLine.ticket_id)
        .where(*tf)
    ) or 0

    # Won total + biggest single win.
    won_stmt = (
        select(
            func.coalesce(func.sum(TicketResult.amount_won_cents), 0),
            func.coalesce(func.max(TicketResult.amount_won_cents), 0),
        )
        .select_from(TicketResult)
        .join(PlayLine, PlayLine.id == TicketResult.play_line_id)
        .join(Ticket, Ticket.id == PlayLine.ticket_id)
        .where(*tf, TicketResult.status == "won")
    )
    total_won, biggest_win = db.execute(won_stmt).one()

    # Winning lines = distinct play_lines with any 'won' result.
    winning_lines = db.scalar(
        select(func.count(func.distinct(PlayLine.id)))
        .select_from(PlayLine)
        .join(Ticket, Ticket.id == PlayLine.ticket_id)
        .join(TicketResult, TicketResult.play_line_id == PlayLine.id)
        .where(*tf, TicketResult.status == "won")
    ) or 0

    pending_cents = _pending_cents(db, tf)

    win_rate = (winning_lines / lines_played) if lines_played else 0
    net = total_won - total_spent
    roi_pct = round(net / total_spent * 100, 1) if total_spent else 0.0

    return {
        "total_spent_cents": int(total_spent),
        "total_won_cents": int(total_won),
        "net_cents": int(net),
        "tickets_purchased": int(tickets_purchased),
        "lines_played": int(lines_played),
        "win_rate": win_rate,
        "biggest_win_cents": int(biggest_win),
        "roi_pct": roi_pct,
        "pending_cents": int(pending_cents),
    }


def _pending_cents(db: Session, ticket_conds) -> int:
    """Sum cost of tickets that have any unsettled play_line.

    A play_line is unsettled if it has a 'pending' TicketResult or no result at all.
    """
    # Per play_line: count of results, count of pending results.
    line_stats = (
        select(
            PlayLine.ticket_id.label("ticket_id"),
            func.count(TicketResult.id).label("n_results"),
            func.count(TicketResult.id)
            .filter(TicketResult.status == "pending")
            .label("n_pending"),
        )
        .select_from(PlayLine)
        .outerjoin(TicketResult, TicketResult.play_line_id == PlayLine.id)
        .group_by(PlayLine.id, PlayLine.ticket_id)
        .subquery()
    )
    # Tickets with at least one unsettled line.
    pending_ticket_ids = (
        select(line_stats.c.ticket_id)
        .where((line_stats.c.n_results == 0) | (line_stats.c.n_pending > 0))
        .distinct()
    )
    stmt = (
        select(func.coalesce(func.sum(Ticket.total_cost_cents), 0))
        .where(*ticket_conds, Ticket.id.in_(pending_ticket_ids))
    )
    return int(db.scalar(stmt) or 0)


def by_game(
    db: Session,
    user: User,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    tf = _ticket_filter(user, date_from, date_to)

    # Spent + ticket count per game.
    spent_rows = db.execute(
        select(
            Game.key,
            Game.display_name,
            func.coalesce(func.sum(Ticket.total_cost_cents), 0),
            func.count(func.distinct(Ticket.id)),
        )
        .select_from(Ticket)
        .join(Game, Game.id == Ticket.game_id)
        .where(*tf)
        .group_by(Game.id, Game.key, Game.display_name)
    ).all()

    # Won per game.
    won_rows = db.execute(
        select(
            Game.key,
            func.coalesce(func.sum(TicketResult.amount_won_cents), 0),
        )
        .select_from(TicketResult)
        .join(PlayLine, PlayLine.id == TicketResult.play_line_id)
        .join(Ticket, Ticket.id == PlayLine.ticket_id)
        .join(Game, Game.id == Ticket.game_id)
        .where(*tf, TicketResult.status == "won")
        .group_by(Game.key)
    ).all()
    won_by = {k: int(v) for k, v in won_rows}

    out = []
    for key, name, spent, tickets in spent_rows:
        won = won_by.get(key, 0)
        out.append({
            "game_key": key,
            "display_name": name,
            "spent_cents": int(spent),
            "won_cents": won,
            "net_cents": won - int(spent),
            "tickets": int(tickets),
        })
    out.sort(key=lambda r: r["game_key"])
    return out


def over_time(
    db: Session,
    user: User,
    date_from: date | None = None,
    date_to: date | None = None,
    bucket: str = "month",
) -> list[dict]:
    if bucket not in ("month", "week"):
        raise ValueError("bucket must be 'month' or 'week'")
    tf = _ticket_filter(user, date_from, date_to)
    trunc_unit = "month" if bucket == "month" else "week"

    def period_expr(col):
        return func.date_trunc(trunc_unit, col)

    # Spend bucketed by ticket purchase_date.
    spend_period = period_expr(Ticket.purchase_date)
    spent_rows = db.execute(
        select(
            spend_period.label("p"),
            func.coalesce(func.sum(Ticket.total_cost_cents), 0),
        )
        .select_from(Ticket)
        .where(*tf)
        .group_by(spend_period)
    ).all()

    # Winnings attributed to the purchase_date of the ticket the winning line belongs to.
    won_period = period_expr(Ticket.purchase_date)
    won_rows = db.execute(
        select(
            won_period.label("p"),
            func.coalesce(func.sum(TicketResult.amount_won_cents), 0),
        )
        .select_from(TicketResult)
        .join(PlayLine, PlayLine.id == TicketResult.play_line_id)
        .join(Ticket, Ticket.id == PlayLine.ticket_id)
        .where(*tf, TicketResult.status == "won")
        .group_by(won_period)
    ).all()

    def fmt(dt) -> str:
        if bucket == "month":
            return dt.strftime("%Y-%m")
        # ISO week label, e.g. 2026-W02
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"

    spent_by: dict[str, int] = {}
    for p, s in spent_rows:
        spent_by[fmt(p)] = spent_by.get(fmt(p), 0) + int(s)
    won_by: dict[str, int] = {}
    for p, w in won_rows:
        won_by[fmt(p)] = won_by.get(fmt(p), 0) + int(w)

    periods = sorted(set(spent_by) | set(won_by))
    out = []
    for period in periods:
        spent = spent_by.get(period, 0)
        won = won_by.get(period, 0)
        out.append({
            "period": period,
            "spent_cents": spent,
            "won_cents": won,
            "net_cents": won - spent,
        })
    return out


def pick_breakdown(
    db: Session,
    user: User,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    tf = _ticket_filter(user, date_from, date_to)

    # Total lines per quick-pick flag.
    line_rows = db.execute(
        select(PlayLine.is_quick_pick, func.count(PlayLine.id))
        .select_from(PlayLine)
        .join(Ticket, Ticket.id == PlayLine.ticket_id)
        .where(*tf)
        .group_by(PlayLine.is_quick_pick)
    ).all()
    lines_by = {bool(qp): int(n) for qp, n in line_rows}

    # Winning lines per quick-pick flag (distinct lines with any 'won' result).
    win_rows = db.execute(
        select(
            PlayLine.is_quick_pick,
            func.count(func.distinct(PlayLine.id)),
        )
        .select_from(PlayLine)
        .join(Ticket, Ticket.id == PlayLine.ticket_id)
        .join(TicketResult, TicketResult.play_line_id == PlayLine.id)
        .where(*tf, TicketResult.status == "won")
        .group_by(PlayLine.is_quick_pick)
    ).all()
    wins_by = {bool(qp): int(n) for qp, n in win_rows}

    def bucket(qp: bool) -> dict:
        lines = lines_by.get(qp, 0)
        wins = wins_by.get(qp, 0)
        return {
            "lines": lines,
            "wins": wins,
            "win_rate": (wins / lines) if lines else 0,
        }

    return {"quick_pick": bucket(True), "self_pick": bucket(False)}
