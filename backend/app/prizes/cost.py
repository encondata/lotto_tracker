"""Compute the total cost of a ticket in cents.

Cost = per-line base price x lines x num_draws, plus add-on surcharges:

* powerball: power_play adds +100c per line.
* mega_millions: no separate add-on (base price already includes it).
* lotto_texas: extra adds +100c per line.
* texas_two_step: no add-ons.
* daily4: each line costs its wager_cents (defaulting to game.base_price_cents
  when unset); fireball doubles the per-line cost.
"""

from app.models.reference import Game
from app.models.ticket import PlayLine

# Per-line surcharge (cents) for jackpot-style add-ons, keyed by game key.
LINE_SURCHARGE = {
    "powerball": ("power_play", 100),
    "lotto_texas": ("extra", 100),
}


def ticket_cost_cents(game: Game, play_lines: list[PlayLine], add_ons: dict,
                      num_draws: int) -> int:
    add_ons = add_ons or {}
    num_draws = max(1, num_draws)

    if game.key == "daily4":
        total = 0
        fireball = bool(add_ons.get("fireball"))
        for line in play_lines:
            line_cost = line.wager_cents or game.base_price_cents
            if fireball:
                line_cost *= 2
            total += line_cost
        return total * num_draws

    # Jackpot-style games: flat base price per line plus optional surcharge.
    per_line = game.base_price_cents
    surcharge = LINE_SURCHARGE.get(game.key)
    if surcharge is not None:
        flag, amount = surcharge
        if add_ons.get(flag):
            per_line += amount

    return per_line * len(play_lines) * num_draws
