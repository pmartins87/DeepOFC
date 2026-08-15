from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Mapping, Sequence

from .actions import NormalPlacementAction, enumerate_normal_actions
from .decision import evaluate_final_normal_round
from .simulator import apply_normal_action, remaining_physical_cards
from .state import Card, OFCState, PlayerState


@dataclass(frozen=True)
class PenultimateActionValue:
    """Exact EV of one round-4-of-5 Hero action in a last-chance subgame.

    `expected_value` averages the *optimal* final-round value over every possible
    unordered 3-card Hero draw in the supplied chance pool. This is an exact
    expectimax reference, not Monte Carlo.
    """

    action: NormalPlacementAction
    expected_value: float
    min_branch_value: float
    max_branch_value: float
    chance_branches: int


@dataclass(frozen=True)
class PenultimateDecision:
    values: tuple[PenultimateActionValue, ...]
    best_indices: tuple[int, ...]
    chance_pool_size: int
    chance_branches_per_action: int

    @property
    def best_value(self) -> float:
        if not self.best_indices:
            raise ValueError("penultimate decision has no actions")
        return self.values[self.best_indices[0]].expected_value

    @property
    def best_actions(self) -> tuple[PenultimateActionValue, ...]:
        return tuple(self.values[i] for i in self.best_indices)


def _replace_hero_after_action(
    state: OFCState,
    *,
    hero_board,
    new_discards: tuple[Card, ...],
    next_incoming: tuple[Card, ...],
) -> OFCState:
    players: list[PlayerState] = []
    for player in state.players:
        if player.chair != state.hero_chair:
            players.append(player)
            continue
        players.append(
            PlayerState(
                chair=player.chair,
                board=hero_board,
                name=player.name,
                fantasy=False,
                sitting_out=player.sitting_out,
                hidden_discard_count=player.hidden_discard_count,
                hidden_incoming_count=0,
            )
        )

    return OFCState(
        players=tuple(players),
        hero_chair=state.hero_chair,
        dealer_chair=state.dealer_chair,
        acting_chair=state.hero_chair,
        round_index=4,
        hero_incoming=next_incoming,
        hero_discards=new_discards,
        hero_pending=(),
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
        mode=state.mode,
    )


def evaluate_penultimate_normal_round_exact_last_chance(
    state: OFCState,
    *,
    additional_unavailable_cards: Sequence[Card] = (),
    future_draw_pool: Sequence[Card] | None = None,
    fantasy_continuation_by_cards: Mapping[int, float] | None = None,
    equality_allowed: bool = True,
) -> PenultimateDecision:
    """Solve Hero's penultimate normal street by exact one-step expectimax.

    Scope is intentionally explicit and narrow: after Hero commits the current
    round-3 (0-based index 3) action, **Hero is the only player who will receive
    another draw** before terminal scoring. Therefore every opponent board must
    already be complete. This is a useful exact subgame/reference kernel, not a
    claim that every live round-3 KKPoker state has this structure.

    The caller may provide identities of physically unavailable cards that are
    absent from Hero's canonical observation (for example simulator-known hidden
    opponent discards). Without those identities a full-deck calculation would
    incorrectly allow dead cards to be drawn.

    `future_draw_pool` is optional. When omitted, every physically remaining card
    is used. When supplied, it must be a unique subset of the true remaining
    physical deck and defines a reduced exact chance subgame; this is useful for
    regression/exploitability tests and never masquerades as the live deck.

    For each current legal action:

      action -> board with 11 committed cards -> every C(pool,3) next draw ->
      exact final-round solver -> arithmetic mean of optimal terminal values.
    """

    if state.hero_is_fantasy:
        raise ValueError("penultimate normal expectimax does not accept Fantasy state")
    if state.round_index != 3:
        raise ValueError("penultimate exact expectimax requires round_index=3")
    if state.acting_chair != state.hero_chair or not state.action_required:
        raise ValueError("state is not an actionable Hero decision")
    hero = state.player(state.hero_chair)
    if hero.board.filled_count() != 9:
        raise ValueError("round_index=3 Hero board must contain exactly 9 committed cards")
    if len(state.hero_incoming) != 3:
        raise ValueError("penultimate normal street requires exactly 3 incoming cards")

    opponent_boards = tuple(
        player.board for player in state.players if player.chair != state.hero_chair
    )
    if not opponent_boards or not all(board.is_complete() for board in opponent_boards):
        raise ValueError(
            "exact last-chance subgame requires every opponent board to be complete"
        )

    extra = tuple(additional_unavailable_cards)
    unavailable = (*state.known_cards(), *extra)
    if len(unavailable) != len(set(unavailable)):
        raise ValueError("known/additional unavailable physical cards must be unique")

    true_remaining = remaining_physical_cards(unavailable)
    true_remaining_set = set(true_remaining)
    if future_draw_pool is None:
        pool = tuple(true_remaining)
    else:
        pool = tuple(future_draw_pool)
        if len(pool) != len(set(pool)):
            raise ValueError("future_draw_pool contains duplicate physical cards")
        missing = set(pool) - true_remaining_set
        if missing:
            raise ValueError(
                "future_draw_pool contains cards that are not physically drawable: "
                + ", ".join(sorted(card.code for card in missing))
            )
    if len(pool) < 3:
        raise ValueError("future draw pool must contain at least 3 cards")

    draws = tuple(combinations(pool, 3))
    expected_draws = comb(len(pool), 3)
    if len(draws) != expected_draws:
        raise AssertionError("chance enumeration cardinality mismatch")

    current_actions = enumerate_normal_actions(state)
    if not current_actions:
        raise RuntimeError("penultimate action generator returned no actions")

    values: list[PenultimateActionValue] = []
    for action in current_actions:
        board_after, discarded_now = apply_normal_action(
            hero.board,
            action,
            round_index=3,
            incoming=state.hero_incoming,
        )
        if board_after.filled_count() != 11:
            raise AssertionError("penultimate action must leave 11 committed Hero cards")
        all_hero_discards = (*state.hero_discards, *discarded_now)

        branch_values: list[float] = []
        for draw in draws:
            future_state = _replace_hero_after_action(
                state,
                hero_board=board_after,
                new_discards=all_hero_discards,
                next_incoming=tuple(draw),
            )
            terminal = evaluate_final_normal_round(
                future_state,
                opponent_boards,
                fantasy_continuation_by_cards=fantasy_continuation_by_cards,
                equality_allowed=equality_allowed,
            )
            branch_values.append(terminal.best_value)

        expected = sum(branch_values) / len(branch_values)
        values.append(
            PenultimateActionValue(
                action=action,
                expected_value=expected,
                min_branch_value=min(branch_values),
                max_branch_value=max(branch_values),
                chance_branches=len(branch_values),
            )
        )

    best = max(value.expected_value for value in values)
    eps = 1e-12
    best_indices = tuple(
        i for i, value in enumerate(values)
        if abs(value.expected_value - best) <= eps
    )
    return PenultimateDecision(
        values=tuple(values),
        best_indices=best_indices,
        chance_pool_size=len(pool),
        chance_branches_per_action=expected_draws,
    )
