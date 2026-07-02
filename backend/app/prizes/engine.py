"""Compute the winnings for a single play line against a draw.

Applies tier resolution, fixed vs. pari-mutuel/jackpot payout lookup, and all
add-on / multiplier / cap rules per game.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.draw import Draw
from app.models.reference import Game, PrizeRule
from app.models.ticket import PlayLine
from app.prizes.matching import DAILY_KEYS, match_line

# Powerball Match-5 ("5") with Power Play is capped at $2,000,000.
POWERBALL_MATCH5_CAP_CENTS = 200_000_000

# Lotto Texas Extra! add-on: fixed cents added on top of the base tier amount.
# Includes a match-2 Extra!-only prize. Never applies to the jackpot ("6").
LOTTO_EXTRA_ADD_CENTS = {
    "5": 10_000_00,
    "4": 100_00,
    "3": 10_00,
    "2": 2_00,
}


@dataclass
class WinResult:
    tier_key: str | None
    match_main: int
    match_special: bool
    amount_cents: int
    amount_pending: bool
    status: str  # "won" | "no_win"


def _load_rules(session: Session, game: Game) -> list[PrizeRule]:
    return list(
        session.scalars(
            select(PrizeRule).where(PrizeRule.game_id == game.id)
        ).all()
    )


def _resolve_jackpot_rule(rules: list[PrizeRule], match_main: int,
                          match_special: bool) -> PrizeRule | None:
    for rule in rules:
        if rule.play_type is not None:
            continue
        if rule.match_main == match_main and rule.match_special == match_special:
            return rule
    return None


def _resolve_daily_rule(rules: list[PrizeRule], tier_key: str) -> PrizeRule | None:
    for rule in rules:
        if rule.tier_key == tier_key:
            return rule
    return None


def _no_win(mr) -> WinResult:
    return WinResult(
        tier_key=None,
        match_main=mr.match_main,
        match_special=mr.match_special,
        amount_cents=0,
        amount_pending=False,
        status="no_win",
    )


def _pari_mutuel_amount(draw: Draw, tier_key: str) -> tuple[int, bool]:
    """Return (amount_cents, pending) for a tier with no fixed base amount."""
    if draw.payouts and tier_key in draw.payouts:
        return int(draw.payouts[tier_key]), False
    return 0, True


def _compute_daily4(rules, game: Game, play_line: PlayLine, draw: Draw,
                    add_ons: dict) -> WinResult:
    mr = match_line(game, play_line, draw)
    if mr.tier_key is None:
        return _no_win(mr)

    rule = _resolve_daily_rule(rules, mr.tier_key)
    if rule is None or rule.base_amount_cents is None:
        return _no_win(mr)

    # base_amount_cents are for a $1 wager; scale by wager.
    wager_cents = play_line.wager_cents or game.base_price_cents
    amount = rule.base_amount_cents * wager_cents // 100

    # TODO fireball: full Fireball matrix deferred. When add_ons["fireball"] is
    # set we currently return the normal (non-fireball) result unchanged.
    _ = add_ons.get("fireball")

    return WinResult(
        tier_key=mr.tier_key,
        match_main=mr.match_main,
        match_special=mr.match_special,
        amount_cents=amount,
        amount_pending=False,
        status="won",
    )


def _compute_jackpot(rules, game: Game, play_line: PlayLine, draw: Draw,
                     add_ons: dict) -> WinResult:
    mr = match_line(game, play_line, draw)
    rule = _resolve_jackpot_rule(rules, mr.match_main, mr.match_special)
    if rule is None:
        return _no_win(mr)

    tier_key = rule.tier_key

    # Pari-mutuel / jackpot tiers (no fixed base): look up payouts.
    # Jackpot tiers are never multiplied; since they carry no fixed base amount
    # they naturally fall into this payout-lookup branch and skip multipliers.
    if rule.base_amount_cents is None:
        amount, pending = _pari_mutuel_amount(draw, tier_key)
        return WinResult(
            tier_key=tier_key,
            match_main=mr.match_main,
            match_special=mr.match_special,
            amount_cents=amount,
            amount_pending=pending,
            status="won",
        )

    # Fixed-amount tier.
    amount = rule.base_amount_cents

    if game.key == "powerball":
        if add_ons.get("power_play"):
            mult = draw.multiplier or 1
            amount = amount * mult
            if tier_key == "5":  # Match 5 cap
                amount = min(amount, POWERBALL_MATCH5_CAP_CENTS)
    elif game.key == "mega_millions":
        # Built-in multiplier always applies to non-jackpot fixed tiers.
        mult = draw.multiplier or 1
        amount = amount * mult
    elif game.key == "lotto_texas":
        if add_ons.get("extra") and tier_key in LOTTO_EXTRA_ADD_CENTS:
            amount = amount + LOTTO_EXTRA_ADD_CENTS[tier_key]
    # texas_two_step: no add-ons.

    return WinResult(
        tier_key=tier_key,
        match_main=mr.match_main,
        match_special=mr.match_special,
        amount_cents=amount,
        amount_pending=False,
        status="won",
    )


def compute_win(session: Session, game: Game, play_line: PlayLine, draw: Draw,
                add_ons: dict) -> WinResult:
    """Compute the win result for one play line against a draw."""
    add_ons = add_ons or {}
    rules = _load_rules(session, game)

    if game.key in DAILY_KEYS:
        return _compute_daily4(rules, game, play_line, draw, add_ons)
    return _compute_jackpot(rules, game, play_line, draw, add_ons)
