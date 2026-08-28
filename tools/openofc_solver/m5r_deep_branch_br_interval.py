from __future__ import annotations

"""Rigorous reduced-game BR intervals with deep opponent-branch pruning."""

from dataclasses import dataclass
import math

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet

AUTHORITY = "RIGOROUS_DEEP_BRANCH_BR_INTERVAL_NOT_ROUTE_CERTIFICATION"
SCHEMA = "openofc-m5r-deep-branch-br-interval-v1"
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
class DeepBranchBRInterval:
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
    skipped_at_round3_prefix: int
    skipped_at_round4_opponent_branch: int
    skipped_at_terminal_opponent_action: int
    zero_reach_skipped_terminal_histories: int
    total_terminal_histories_accounted: int
    terminal_work_fraction: float
    pruned_round3_prefixes: int
    pruned_round4_opponent_branches: int
    pruned_terminal_opponent_actions: int
    schema: str = SCHEMA
    authority: str = AUTHORITY
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _action_intervals(game: HUTwoRoundSubgame, info: TwoRoundInfoSet):
    return {action: _Interval() for action in game.actions(info)}


def deep_branch_best_response_interval(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    player: int,
    *,
    profile_p0_value: float,
    p0_utility_min: float,
    p0_utility_max: float,
    prune_reach_threshold: float,
) -> DeepBranchBRInterval:
    """Bound BR while pruning only chance/opponent counterfactual branches.

    The responding player's own strategy probabilities are never used.  A low
    reach can prune a whole post-round-3 continuation, an opponent-first round-4
    branch, or a final opponent action.  Every responding-player legal action is
    retained in the appropriate information-set maximization.
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

    resolved = 0
    skipped = 0
    skipped_r3 = 0
    skipped_r4_branch = 0
    skipped_terminal_opp = 0
    zero_reach_skipped = 0
    pruned_r3_prefixes = 0
    pruned_r4_branches = 0
    pruned_terminal_actions = 0
    cp = float(game.chance_probability)

    def parent_bucket(info: TwoRoundInfoSet):
        return round3_values.setdefault(info, _action_intervals(game, info))

    def add_skipped(
        bucket: _Interval,
        reach: float,
        descendant_terminals: int,
        *,
        level: str,
    ) -> None:
        nonlocal skipped, skipped_r3, skipped_r4_branch, skipped_terminal_opp
        nonlocal zero_reach_skipped, pruned_r3_prefixes, pruned_r4_branches
        nonlocal pruned_terminal_actions
        bucket.add(reach * own_min, reach * own_max)
        skipped += descendant_terminals
        if reach <= EPS:
            zero_reach_skipped += descendant_terminals
        if level == "r3":
            skipped_r3 += descendant_terminals
            pruned_r3_prefixes += 1
        elif level == "r4_branch":
            skipped_r4_branch += descendant_terminals
            pruned_r4_branches += 1
        elif level == "terminal_opponent":
            if descendant_terminals != 1:
                raise AssertionError("terminal opponent prune must skip one terminal")
            skipped_terminal_opp += 1
            pruned_terminal_actions += 1
        else:
            raise AssertionError(f"unknown prune level: {level}")

    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player
        first_r3_info = game.round3_first_info(outcome)
        first_r3_actions = game.actions(first_r3_info)
        first_r3_dist = (
            game._distribution(profile, first_r3_info) if first != player else None
        )

        for first_r3 in first_r3_actions:
            p_first_r3 = (
                float(first_r3_dist[first_r3]) if first_r3_dist is not None else 1.0
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
                second_r4_actions_template = game._round4_actions(
                    outcome, second, board0, board1
                )
                prefix_reach = cp * p_first_r3 * p_second_r3

                if prefix_reach <= threshold + EPS:
                    add_skipped(
                        parent_bucket(br_r3_info)[br_own_r3],
                        prefix_reach,
                        len(first_r4_actions) * len(second_r4_actions_template),
                        level="r3",
                    )
                    continue

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
                    second_r4_actions = game.actions(second_r4_info)

                    if first != player:
                        # Opponent acts first on round 4.  The responding player
                        # observes this action and gets a distinct r4 infoset, so
                        # a low-reach opponent branch can be replaced directly by
                        # one utility-envelope contribution to the r3 predecessor.
                        opponent_branch_reach = prefix_reach * p_first_r4
                        if opponent_branch_reach <= threshold + EPS:
                            add_skipped(
                                parent_bucket(br_r3_info)[br_own_r3],
                                opponent_branch_reach,
                                len(second_r4_actions),
                                level="r4_branch",
                            )
                            continue

                        br_r4_info = second_r4_info
                        parent = (br_r3_info, br_own_r3)
                        previous = round4_parent.setdefault(br_r4_info, parent)
                        if previous != parent:
                            raise AssertionError(
                                "M5R-E perfect-recall predecessor mismatch"
                            )
                        bucket = round4_values.setdefault(
                            br_r4_info, _action_intervals(game, br_r4_info)
                        )
                        for second_r4 in second_r4_actions:
                            u0 = float(
                                game.terminal_u0(
                                    outcome,
                                    first_r3,
                                    second_r3,
                                    first_r4,
                                    second_r4,
                                )
                            )
                            own_u = u0 if player == 0 else -u0
                            exact = opponent_branch_reach * own_u
                            bucket[second_r4].add(exact, exact)
                            resolved += 1
                        continue

                    # Responding player acts first on round 4.  Every own action
                    # remains explicit.  Only the following opponent action may
                    # be pruned using its frozen probability.
                    br_r4_info = first_r4_info
                    parent = (br_r3_info, br_own_r3)
                    previous = round4_parent.setdefault(br_r4_info, parent)
                    if previous != parent:
                        raise AssertionError("M5R-E perfect-recall predecessor mismatch")
                    bucket = round4_values.setdefault(
                        br_r4_info, _action_intervals(game, br_r4_info)
                    )
                    second_r4_dist = game._distribution(profile, second_r4_info)
                    for second_r4 in second_r4_actions:
                        p_second_r4 = float(second_r4_dist[second_r4])
                        opponent_terminal_reach = prefix_reach * p_second_r4
                        if opponent_terminal_reach <= threshold + EPS:
                            add_skipped(
                                bucket[first_r4],
                                opponent_terminal_reach,
                                1,
                                level="terminal_opponent",
                            )
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
                        own_u = u0 if player == 0 else -u0
                        exact = opponent_terminal_reach * own_u
                        bucket[first_r4].add(exact, exact)
                        resolved += 1

    for info, action_intervals in round4_values.items():
        lower_best = max(interval.lower for interval in action_intervals.values())
        upper_best = max(interval.upper for interval in action_intervals.values())
        parent_info, parent_action = round4_parent[info]
        parent_bucket(parent_info)[parent_action].add(lower_best, upper_best)

    lower_total = 0.0
    upper_total = 0.0
    for action_intervals in round3_values.values():
        lower_total += max(interval.lower for interval in action_intervals.values())
        upper_total += max(interval.upper for interval in action_intervals.values())

    if lower_total > upper_total + 1e-12:
        raise AssertionError("M5R-E interval inverted")
    total = resolved + skipped
    if total <= 0:
        raise AssertionError("M5R-E accounted no terminal histories")

    return DeepBranchBRInterval(
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
        resolved_terminal_histories=resolved,
        skipped_terminal_histories=skipped,
        skipped_at_round3_prefix=skipped_r3,
        skipped_at_round4_opponent_branch=skipped_r4_branch,
        skipped_at_terminal_opponent_action=skipped_terminal_opp,
        zero_reach_skipped_terminal_histories=zero_reach_skipped,
        total_terminal_histories_accounted=total,
        terminal_work_fraction=resolved / total,
        pruned_round3_prefixes=pruned_r3_prefixes,
        pruned_round4_opponent_branches=pruned_r4_branches,
        pruned_terminal_opponent_actions=pruned_terminal_actions,
    )
