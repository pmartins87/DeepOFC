from __future__ import annotations

"""Rigorous frozen-policy BR intervals with round-3 prefix subtree pruning.

The implementation is intentionally reduced-game only.  It never calls the exact
best-response oracle or the full-profile expected-value evaluator internally.
Those remain independent validation authorities outside this module.
"""

from dataclasses import dataclass
import math
from typing import Mapping

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet

AUTHORITY = "RIGOROUS_PREFIX_SUBTREE_BR_INTERVAL_NOT_ROUTE_CERTIFICATION"
SCHEMA = "openofc-m5r-prefix-subtree-br-interval-v1"
EPS = 1e-15


@dataclass
class _Interval:
    lower: float = 0.0
    upper: float = 0.0

    def add(self, lower: float, upper: float) -> None:
        lo = float(lower)
        hi = float(upper)
        if lo > hi + EPS:
            raise ValueError("invalid interval contribution")
        self.lower += lo
        self.upper += hi


@dataclass(frozen=True)
class PrefixSubtreeBRInterval:
    player: int
    prune_reach_threshold: float
    profile_p0_value: float
    own_profile_value: float
    utility_lower: float
    utility_upper: float
    lower_br_value: float
    upper_br_value: float
    lower_deviation_gain: float
    upper_deviation_gain: float
    interval_width: float
    resolved_terminal_histories: int
    skipped_terminal_histories: int
    zero_reach_skipped_terminal_histories: int
    total_terminal_histories_accounted: int
    terminal_work_fraction: float
    pruned_round3_prefixes: int
    exact_round3_prefixes: int
    pruned_counterfactual_reach_mass: float
    maximum_pruned_prefix_reach: float
    schema: str = SCHEMA
    authority: str = AUTHORITY
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _new_action_intervals(
    game: HUTwoRoundSubgame,
    info: TwoRoundInfoSet,
) -> dict[NormalPlacementAction, _Interval]:
    return {action: _Interval() for action in game.actions(info)}


def prefix_subtree_best_response_interval(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    player: int,
    *,
    profile_p0_value: float,
    p0_utility_min: float,
    p0_utility_max: float,
    prune_reach_threshold: float,
) -> PrefixSubtreeBRInterval:
    """Bound one player's BR while skipping low-reach round-4 continuations.

    The pruning decision is made only after both round-3 actions are known.  At
    that point the responding player's round-3 infoset and exact own predecessor
    action are known, so a whole skipped continuation can be attached directly
    to that action without breaking perfect-recall coupling.

    The caller supplies the frozen profile value independently.  This function
    deliberately does not call ``game.expected_u0`` or any exact BR routine.
    """

    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    threshold = _finite(prune_reach_threshold, "prune_reach_threshold")
    if threshold < 0.0:
        raise ValueError("prune_reach_threshold must be non-negative")
    p0_min = _finite(p0_utility_min, "p0_utility_min")
    p0_max = _finite(p0_utility_max, "p0_utility_max")
    if p0_min > p0_max:
        raise ValueError("p0 utility envelope must be ordered")
    p0_value = _finite(profile_p0_value, "profile_p0_value")
    own_min, own_max = (
        (p0_min, p0_max) if player == 0 else (-p0_max, -p0_min)
    )
    own_profile = p0_value if player == 0 else -p0_value

    round4_values: dict[
        TwoRoundInfoSet,
        dict[NormalPlacementAction, _Interval],
    ] = {}
    round4_parent: dict[
        TwoRoundInfoSet,
        tuple[TwoRoundInfoSet, NormalPlacementAction],
    ] = {}
    round3_values: dict[
        TwoRoundInfoSet,
        dict[NormalPlacementAction, _Interval],
    ] = {}

    resolved_terminals = 0
    skipped_terminals = 0
    zero_reach_skipped = 0
    pruned_prefixes = 0
    exact_prefixes = 0
    pruned_mass = 0.0
    max_pruned_reach = 0.0
    cp = float(game.chance_probability)

    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player
        first_r3_info = game.round3_first_info(outcome)
        first_r3_actions = game.actions(first_r3_info)
        first_r3_dist = (
            game._distribution(profile, first_r3_info)
            if first != player
            else None
        )

        for first_r3 in first_r3_actions:
            p_first_r3 = (
                float(first_r3_dist[first_r3])
                if first_r3_dist is not None
                else 1.0
            )
            second_r3_info = game.round3_second_info(outcome, first_r3)
            second_r3_actions = game.actions(second_r3_info)
            second_r3_dist = (
                game._distribution(profile, second_r3_info)
                if second != player
                else None
            )

            for second_r3 in second_r3_actions:
                p_second_r3 = (
                    float(second_r3_dist[second_r3])
                    if second_r3_dist is not None
                    else 1.0
                )
                board0, board1, action0_r3, action1_r3 = game._boards_after_round3(
                    outcome, first_r3, second_r3
                )
                first_own_r3 = action0_r3 if first == 0 else action1_r3
                first_opp_r3 = action1_r3 if first == 0 else action0_r3
                second_own_r3 = action0_r3 if second == 0 else action1_r3
                second_opp_r3 = action1_r3 if second == 0 else action0_r3
                br_r3_info = first_r3_info if player == first else second_r3_info
                br_own_r3 = first_own_r3 if player == first else second_own_r3

                first_r4_info = game.round4_info(
                    outcome,
                    player=first,
                    own_round3_action=first_own_r3,
                    opponent_round3_action=first_opp_r3,
                    current_first_action=None,
                )
                first_r4_actions = game.actions(first_r4_info)
                second_r4_actions = game._round4_actions(
                    outcome, second, board0, board1
                )
                descendant_terminals = len(first_r4_actions) * len(second_r4_actions)
                prefix_reach = cp * p_first_r3 * p_second_r3

                parent_bucket = round3_values.setdefault(
                    br_r3_info,
                    _new_action_intervals(game, br_r3_info),
                )

                if prefix_reach <= threshold + EPS:
                    parent_bucket[br_own_r3].add(
                        prefix_reach * own_min,
                        prefix_reach * own_max,
                    )
                    pruned_prefixes += 1
                    skipped_terminals += descendant_terminals
                    pruned_mass += prefix_reach
                    max_pruned_reach = max(max_pruned_reach, prefix_reach)
                    if prefix_reach <= EPS:
                        zero_reach_skipped += descendant_terminals
                    continue

                exact_prefixes += 1
                first_r4_dist = (
                    game._distribution(profile, first_r4_info)
                    if first != player
                    else None
                )

                for first_r4 in first_r4_actions:
                    p_first_r4 = (
                        float(first_r4_dist[first_r4])
                        if first_r4_dist is not None
                        else 1.0
                    )
                    second_r4_info = game.round4_info(
                        outcome,
                        player=second,
                        own_round3_action=second_own_r3,
                        opponent_round3_action=second_opp_r3,
                        current_first_action=first_r4,
                    )
                    second_r4_actions_here = game.actions(second_r4_info)
                    second_r4_dist = (
                        game._distribution(profile, second_r4_info)
                        if second != player
                        else None
                    )
                    br_r4_info = (
                        first_r4_info if player == first else second_r4_info
                    )
                    parent = (br_r3_info, br_own_r3)
                    previous_parent = round4_parent.setdefault(br_r4_info, parent)
                    if previous_parent != parent:
                        raise AssertionError(
                            "M5R prefix pruning perfect-recall predecessor mismatch"
                        )
                    bucket = round4_values.setdefault(
                        br_r4_info,
                        _new_action_intervals(game, br_r4_info),
                    )

                    for second_r4 in second_r4_actions_here:
                        p_second_r4 = (
                            float(second_r4_dist[second_r4])
                            if second_r4_dist is not None
                            else 1.0
                        )
                        own_r4 = first_r4 if player == first else second_r4
                        opponent_reach = prefix_reach * p_first_r4 * p_second_r4
                        if opponent_reach <= EPS:
                            skipped_terminals += 1
                            zero_reach_skipped += 1
                            continue
                        u0 = float(
                            game.terminal_u0(
                                outcome,
                                first_r3,
                                second_r3,
                                first_r4,
                                second_r4,
                            )
                        )
                        own_utility = u0 if player == 0 else -u0
                        exact_contribution = opponent_reach * own_utility
                        bucket[own_r4].add(exact_contribution, exact_contribution)
                        resolved_terminals += 1

    # Resolve every explicitly traversed round-4 infoset.  The interval max is
    # valid even if a future extension introduces interval-valued round-4 action
    # contributions, so this propagation remains reusable.
    for info, action_intervals in round4_values.items():
        lower_best = max(interval.lower for interval in action_intervals.values())
        upper_best = max(interval.upper for interval in action_intervals.values())
        parent_info, parent_action = round4_parent[info]
        parent_bucket = round3_values.setdefault(
            parent_info,
            _new_action_intervals(game, parent_info),
        )
        parent_bucket[parent_action].add(lower_best, upper_best)

    lower_total = 0.0
    upper_total = 0.0
    for action_intervals in round3_values.values():
        lower_total += max(interval.lower for interval in action_intervals.values())
        upper_total += max(interval.upper for interval in action_intervals.values())

    if lower_total > upper_total + 1e-12:
        raise AssertionError("M5R prefix-pruned BR interval inverted")
    total_accounted = resolved_terminals + skipped_terminals
    if total_accounted <= 0:
        raise AssertionError("M5R prefix-pruned BR accounted no terminal histories")

    return PrefixSubtreeBRInterval(
        player=player,
        prune_reach_threshold=threshold,
        profile_p0_value=p0_value,
        own_profile_value=own_profile,
        utility_lower=own_min,
        utility_upper=own_max,
        lower_br_value=lower_total,
        upper_br_value=upper_total,
        lower_deviation_gain=lower_total - own_profile,
        upper_deviation_gain=upper_total - own_profile,
        interval_width=upper_total - lower_total,
        resolved_terminal_histories=resolved_terminals,
        skipped_terminal_histories=skipped_terminals,
        zero_reach_skipped_terminal_histories=zero_reach_skipped,
        total_terminal_histories_accounted=total_accounted,
        terminal_work_fraction=resolved_terminals / total_accounted,
        pruned_round3_prefixes=pruned_prefixes,
        exact_round3_prefixes=exact_prefixes,
        pruned_counterfactual_reach_mass=pruned_mass,
        maximum_pruned_prefix_reach=max_pruned_reach,
    )
