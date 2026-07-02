"""Prize engine: matching, winnings computation, and ticket cost."""

from app.prizes.matching import MatchResult, match_line
from app.prizes.engine import WinResult, compute_win
from app.prizes.cost import ticket_cost_cents

__all__ = [
    "MatchResult",
    "match_line",
    "WinResult",
    "compute_win",
    "ticket_cost_cents",
]
