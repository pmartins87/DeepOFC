from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb, sqrt
import random
from typing import Mapping, Sequence

from .actions import NormalPlacementAction, enumerate_normal_actions
from .decision import evaluate_final_normal_round
from .expectimax import _replace_hero_after_action
from .simulator import apply_normal_action, remaining_physical_cards
from .state import Card, OFCState


@dataclass(frozen=True)
class MonteCarloActionValue:
    action: NormalPlacementAction
    mean_value: float
    standard_error: float
    ci95_half_width: float
    min_sample_value: float
    max_sample_value: float
    samples: int


@dataclass(frozen=True)
class MonteCarloDecision:
    values: tuple[MonteCarloActionValue, ...]
    best_indices: tuple[int, ...]
    chance_pool_size: int
    total_chance_branches: int
    sampled_chance_branches: int
    seed: int
    exhaustive: bool

    @property
    def best_value(self) -> float:
        if not self.best_indices:
            raise ValueError("Monte Carlo decision has no actions")
        return self.values[self.best_indices[0]].mean_value

    @property
    def best_actions(self) -> tuple[MonteCarloActionValue, ...]:
        return tuple(self.values[i] for i in self.best_indices)


def _validate_scope_and_pool(
    state: OFCState,
    *,
    additional_unavailable_cards: Sequence[Card],
    future_draw_pool: Sequence[Card] | None,
) -> tuple[tuple, tuple[Card, ...]]:
    if state.hero_is_fantasy:
        raise ValueError("penultimate normal Monte Carlo does not accept Fantasy state")
    if state.round_index != 3:
        raise ValueError("penultimate Monte Carlo requires round_index=3")
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
        raise ValueError("Monte Carlo reference requires complete opponent boards")

    extra = tuple(additional_unavailable_cards)
    unavailable = (*state.known_cards(), *extra)
    if len(unavailable) != len(set(unavailable)):
        raise ValueError("known/additional unavailable physical cards must be unique")
    remaining = remaining_physical_cards(unavailable)
    remaining_set = set(remaining)

    if future_draw_pool is None:
        pool = tuple(remaining)
    else:
        pool = tuple(future_draw_pool)
        if len(pool) != len(set(pool)):
            raise ValueError("future_draw_pool contains duplicate physical cards")
        missing = set(pool) - remaining_set
        if missing:
            raise ValueError(
                "future_draw_pool contains cards that are not physically drawable: "
                + ", ".join(sorted(card.code for card in missing))
            )
    if len(pool) < 3:
        raise ValueError("future draw pool must contain at least 3 cards")
    return opponent_boards, pool


def _finite_population_standard_error(values: Sequence[float], population: int) -> float:
    n = len(values)
    if n <= 1 or n >= population:
        return 0.0
    mean = sum(values) / n
    sample_variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    # Exact finite-population correction for uniform sampling without replacement.
    fpc = sqrt((population - n) / (population - 1))
    return sqrt(sample_variance / n) * fpc


def evaluate_penultimate_normal_round_monte_carlo(
    state: OFCState,
    *,
    samples: int,
    seed: int,
    additional_unavailable_cards: Sequence[Card] = (),
    future_draw_pool: Sequence[Card] | None = None,
    fantasy_continuation_by_cards: Mapping[int, float] | None = None,
    equality_allowed: bool = True,
) -> MonteCarloDecision:
    """Finite-population Monte Carlo baseline for the exact last-chance subgame.

    The chance space is the set of all unordered 3-card draws from the validated
    physical pool. A deterministic RNG samples chance branches **without
    replacement**, and the same sampled draws are reused for every current Hero
    action (common random numbers) so action differences are less noisy.

    If `samples >= C(pool,3)`, every branch is evaluated and this function must
    become exactly equal to the exhaustive expectimax reference. Otherwise the
    reported 95% half-width is `1.96 * standard_error` with finite-population
    correction. It is a diagnostic normal-approximation interval, not a formal
    worst-case EV bound.
    """

    if samples <= 0:
        raise ValueError("samples must be positive")
    opponent_boards, pool = _validate_scope_and_pool(
        state,
        additional_unavailable_cards=additional_unavailable_cards,
        future_draw_pool=future_draw_pool,
    )
    population = comb(len(pool), 3)
    all_draws = tuple(combinations(pool, 3))
    if len(all_draws) != population:
        raise AssertionError("chance population cardinality mismatch")

    sample_count = min(samples, population)
    if sample_count == population:
        sampled_draws = all_draws
        exhaustive = True
    else:
        rng = random.Random(seed)
        sampled_draws = tuple(rng.sample(all_draws, sample_count))
        exhaustive = False

    hero = state.player(state.hero_chair)
    current_actions = enumerate_normal_actions(state)
    if not current_actions:
        raise RuntimeError("penultimate action generator returned no actions")

    values: list[MonteCarloActionValue] = []
    for action in current_actions:
        board_after, discarded_now = apply_normal_action(
            hero.board,
            action,
            round_index=3,
            incoming=state.hero_incoming,
        )
        all_hero_discards = (*state.hero_discards, *discarded_now)
        branch_values: list[float] = []

        for draw in sampled_draws:
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

        mean = sum(branch_values) / len(branch_values)
        se = _finite_population_standard_error(branch_values, population)
        values.append(
            MonteCarloActionValue(
                action=action,
                mean_value=mean,
                standard_error=se,
                ci95_half_width=1.96 * se,
                min_sample_value=min(branch_values),
                max_sample_value=max(branch_values),
                samples=len(branch_values),
            )
        )

    best = max(value.mean_value for value in values)
    eps = 1e-12
    best_indices = tuple(
        i for i, value in enumerate(values)
        if abs(value.mean_value - best) <= eps
    )
    return MonteCarloDecision(
        values=tuple(values),
        best_indices=best_indices,
        chance_pool_size=len(pool),
        total_chance_branches=population,
        sampled_chance_branches=sample_count,
        seed=int(seed),
        exhaustive=exhaustive,
    )
