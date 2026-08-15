from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .actions import NormalPlacementAction, enumerate_normal_actions
from .scoring import is_foul
from .simulator import apply_normal_action, normal_fantasy_entry_cards, settle_raw_points
from .state import OFCState, PlayerBoard


@dataclass(frozen=True)
class TerminalActionValue:
    """Exact value of a final normal-round placement under frozen raw scoring.

    `current_hand_points` is exact against the supplied complete opponent boards.
    `continuation_points` is an explicit caller-supplied value for earning the
    next Fantasy hand. Keeping the continuation value external prevents the
    engine from silently inventing a value for Fantasy before R5/R6 solve it.
    """

    action: NormalPlacementAction
    board: PlayerBoard
    current_hand_points: int
    fantasy_entry_cards: int | None
    continuation_points: float
    total_value: float
    foul: bool


@dataclass(frozen=True)
class TerminalDecision:
    values: tuple[TerminalActionValue, ...]
    best_indices: tuple[int, ...]

    @property
    def best_value(self) -> float:
        if not self.best_indices:
            raise ValueError("terminal decision has no actions")
        return self.values[self.best_indices[0]].total_value

    @property
    def best_actions(self) -> tuple[TerminalActionValue, ...]:
        return tuple(self.values[i] for i in self.best_indices)


def evaluate_final_normal_round(
    state: OFCState,
    opponent_boards: Sequence[PlayerBoard],
    *,
    fantasy_continuation_by_cards: Mapping[int, float] | None = None,
    equality_allowed: bool = True,
) -> TerminalDecision:
    """Solve Hero's fifth/last normal Pineapple placement exactly.

    This is the first R5 decision kernel that is mathematically exact rather
    than heuristic. It covers all UI-legal `place two / discard one` actions,
    materializes Hero's completed board, applies board-aware Joker semantics,
    scores Hero pairwise versus every supplied complete opponent board, and
    adds an *explicit* continuation value if the result enters 14/15/16/17-card
    Fantasy.

    With continuation values all zero this is exact for current-hand raw OFC
    points only. It is not yet the full infinite-horizon game solution because
    the true value of earning Fantasy must itself be solved.
    """

    if state.hero_is_fantasy:
        raise ValueError("Fantasy uses a separate one-shot decision problem")
    if state.round_index != 4:
        raise ValueError("exact terminal normal solver requires round_index=4")
    if state.acting_chair != state.hero_chair or not state.action_required:
        raise ValueError("state is not a Hero decision state")
    hero_board = state.player(state.hero_chair).board
    if hero_board.filled_count() != 11:
        raise ValueError("round 4 Hero board must contain exactly 11 committed cards")
    if len(opponent_boards) != len(state.players) - 1:
        raise ValueError("must supply one complete board for every opponent")
    if not all(board.is_complete() for board in opponent_boards):
        raise ValueError("terminal exact scoring requires complete opponent boards")

    continuation = dict(fantasy_continuation_by_cards or {})
    illegal_keys = set(continuation) - {14, 15, 16, 17}
    if illegal_keys:
        raise ValueError(f"unsupported Fantasy continuation keys: {sorted(illegal_keys)}")

    values: list[TerminalActionValue] = []
    for action in enumerate_normal_actions(state):
        completed, _ = apply_normal_action(
            hero_board,
            action,
            round_index=4,
            incoming=state.hero_incoming,
        )
        # Hero is canonical chair 0 in this local settlement vector. Opponent
        # order is irrelevant because pairwise points simply add.
        raw = settle_raw_points(
            (completed, *opponent_boards),
            equality_allowed=equality_allowed,
        )
        current = raw.points_by_chair[0]
        fantasy_cards = normal_fantasy_entry_cards(
            completed,
            equality_allowed=equality_allowed,
        )
        future = 0.0 if fantasy_cards is None else float(continuation.get(fantasy_cards, 0.0))
        values.append(
            TerminalActionValue(
                action=action,
                board=completed,
                current_hand_points=current,
                fantasy_entry_cards=fantasy_cards,
                continuation_points=future,
                total_value=float(current) + future,
                foul=is_foul(completed, equality_allowed=equality_allowed),
            )
        )

    if not values:
        raise RuntimeError("round 4 action generator returned no actions")
    best = max(value.total_value for value in values)
    # Exact current points are integers; continuation values may be floats from a
    # future solver. Use a tiny tolerance only for equality of supplied values.
    eps = 1e-12
    best_indices = tuple(
        i for i, value in enumerate(values)
        if abs(value.total_value - best) <= eps
    )
    return TerminalDecision(tuple(values), best_indices)
