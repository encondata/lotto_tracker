"""Determine how a play line matches a draw and which prize tier it hits.

Two families of games:

* Jackpot-style (powerball, mega_millions, lotto_texas, texas_two_step):
  matching is by count of shared main numbers plus an optional special-ball
  match. The resulting ``(match_main, match_special)`` pair identifies a tier.
* Daily 4: matching is by ``play_type`` (straight / box / combo / pair-*).
  The tier_key is the play-type (or box multiplicity tier).
"""

from collections import Counter
from dataclasses import dataclass

from app.models.draw import Draw
from app.models.reference import Game
from app.models.ticket import PlayLine

# Games whose matching is play-type driven rather than count driven.
DAILY_KEYS = {"daily4"}


@dataclass
class MatchResult:
    match_main: int
    match_special: bool
    tier_key: str | None


def _box_tier_for_play(main_numbers: list[int]) -> str | None:
    """Return the box tier for a play based on its digit multiplicity pattern.

    all distinct -> 24-way, one pair -> 12-way, two pair -> 6-way,
    three of a kind -> 4-way, four of a kind -> straight-only (no box).
    """
    counts = sorted(Counter(main_numbers).values(), reverse=True)
    if counts == [1, 1, 1, 1]:
        return "box-24"
    if counts == [2, 1, 1]:
        return "box-12"
    if counts == [2, 2]:
        return "box-6"
    if counts == [3, 1]:
        return "box-4"
    # [4] -> four of a kind: no box play possible.
    return None


def _match_daily4(play_line: PlayLine, draw: Draw) -> MatchResult:
    play = list(play_line.main_numbers)
    winning = list(draw.winning_main)
    play_type = play_line.play_type or "straight"

    if play_type == "straight":
        tier = "straight" if play == winning else None
        return MatchResult(match_main=len(play), match_special=False, tier_key=tier)

    if play_type == "combo":
        # Combo pays as a straight when the exact ordered numbers match.
        tier = "straight" if play == winning else None
        return MatchResult(match_main=len(play), match_special=False, tier_key=tier)

    if play_type == "box":
        if sorted(play) == sorted(winning):
            tier = _box_tier_for_play(play)
        else:
            tier = None
        return MatchResult(match_main=len(play), match_special=False, tier_key=tier)

    if play_type in ("pair-front", "pair-mid", "pair-back"):
        if play_type == "pair-front":
            sl = slice(0, 2)
        elif play_type == "pair-mid":
            sl = slice(1, 3)
        else:  # pair-back
            sl = slice(2, 4)
        tier = play_type if play[sl] == winning[sl] else None
        return MatchResult(match_main=2, match_special=False, tier_key=tier)

    return MatchResult(match_main=0, match_special=False, tier_key=None)


def _match_jackpot(game: Game, play_line: PlayLine, draw: Draw) -> MatchResult:
    match_main = len(set(play_line.main_numbers) & set(draw.winning_main))
    match_special = bool(
        game.has_special_ball
        and play_line.special_number is not None
        and draw.winning_special is not None
        and play_line.special_number == draw.winning_special
    )
    # tier_key is resolved by the engine against seeded PrizeRules; matching
    # only reports the raw match facts. We leave tier_key None here.
    return MatchResult(
        match_main=match_main, match_special=match_special, tier_key=None
    )


def match_line(game: Game, play_line: PlayLine, draw: Draw) -> MatchResult:
    """Match a play line against a draw.

    For daily4, ``tier_key`` is fully resolved here (play-type / box tier).
    For jackpot-style games, ``tier_key`` is resolved by the engine using the
    game's seeded PrizeRules; here it is left None. To keep ``match_line`` useful
    standalone, we resolve jackpot tier_key when possible via the game's rules.
    """
    if game.key in DAILY_KEYS:
        return _match_daily4(play_line, draw)

    result = _match_jackpot(game, play_line, draw)
    # Resolve tier_key from the game's loaded prize_rules if available.
    tier_key = None
    for rule in game.prize_rules:
        if rule.play_type is not None:
            continue
        if rule.match_main == result.match_main and rule.match_special == result.match_special:
            tier_key = rule.tier_key
            break
    result.tier_key = tier_key
    return result
