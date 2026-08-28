from __future__ import annotations

"""Utility-free target-width planner for M5R-E deep BR pruning."""

from dataclasses import dataclass
import math

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet

AUTHORITY = "RIGOROUS_TARGET_WIDTH_BUDGET_CONTROLLER_NOT_ROUTE_CERTIFICATION"
SCHEMA = "openofc-m5r-target-width-budget-plan-v1"
EPS = 1e-15


@dataclass(frozen=True)
class TargetWidthBudgetPlan:
    player: int
    target_width: float
    selected_prune_reach_threshold: float
    guaranteed_unresolved_br_width_cap: float
    utility_range: float
    planned_resolved_terminal_histories: int
    planned_skipped_terminal_histories: int
    total_terminal_histories: int
    planned_terminal_work_fraction: float
    candidate_threshold_count: int
    feasible_candidate_count: int
    schema: str = SCHEMA
    authority: str = AUTHORITY
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


@dataclass(frozen=True)
class _ThresholdSummary:
    threshold: float
    width_cap: float
    resolved: int
    skipped: int


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _enumerate_reach_thresholds(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    player: int,
) -> tuple[float, ...]:
    reaches = {0.0}
    cp = float(game.chance_probability)
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
                prefix_reach = cp * p_first_r3 * p_second_r3
                reaches.add(prefix_reach)
                board0, board1, action0_r3, action1_r3 = game._boards_after_round3(
                    outcome, first_r3, second_r3
                )
                first_own_r3 = action0_r3 if first == 0 else action1_r3
                first_opp_r3 = action1_r3 if first == 0 else action0_r3
                second_own_r3 = action0_r3 if second == 0 else action1_r3
                second_opp_r3 = action1_r3 if second == 0 else action0_r3
                first_r4_info = game.round4_info(
                    outcome,
                    player=first,
                    own_round3_action=first_own_r3,
                    opponent_round3_action=first_opp_r3,
                    current_first_action=None,
                )
                first_r4_actions = game.actions(first_r4_info)
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
                    if first != player:
                        reaches.add(prefix_reach * p_first_r4)
                    else:
                        second_dist = game._distribution(profile, second_r4_info)
                        for second_r4 in game.actions(second_r4_info):
                            reaches.add(prefix_reach * float(second_dist[second_r4]))
    return tuple(sorted(reach for reach in reaches if reach >= 0.0))


def _summary_for_threshold(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    player: int,
    *,
    utility_range: float,
    threshold: float,
) -> _ThresholdSummary:
    cp = float(game.chance_probability)
    direct_mass: dict[
        tuple[TwoRoundInfoSet, NormalPlacementAction], float
    ] = {}
    r4_skipped_mass: dict[
        TwoRoundInfoSet, dict[NormalPlacementAction, float]
    ] = {}
    r4_parent: dict[
        TwoRoundInfoSet, tuple[TwoRoundInfoSet, NormalPlacementAction]
    ] = {}
    resolved = 0
    skipped = 0

    def add_direct(
        info: TwoRoundInfoSet,
        action: NormalPlacementAction,
        mass: float,
    ) -> None:
        key = (info, action)
        direct_mass[key] = direct_mass.get(key, 0.0) + mass

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
                    add_direct(br_r3_info, br_own_r3, prefix_reach)
                    skipped += len(first_r4_actions) * len(second_r4_actions_template)
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
                        branch_reach = prefix_reach * p_first_r4
                        if branch_reach <= threshold + EPS:
                            add_direct(br_r3_info, br_own_r3, branch_reach)
                            skipped += len(second_r4_actions)
                        else:
                            resolved += len(second_r4_actions)
                        continue

                    br_r4_info = first_r4_info
                    parent = (br_r3_info, br_own_r3)
                    previous = r4_parent.setdefault(br_r4_info, parent)
                    if previous != parent:
                        raise AssertionError("M5R-F perfect-recall predecessor mismatch")
                    masses = r4_skipped_mass.setdefault(
                        br_r4_info,
                        {action: 0.0 for action in game.actions(br_r4_info)},
                    )
                    second_dist = game._distribution(profile, second_r4_info)
                    for second_r4 in second_r4_actions:
                        terminal_reach = prefix_reach * float(second_dist[second_r4])
                        if terminal_reach <= threshold + EPS:
                            masses[first_r4] += terminal_reach
                            skipped += 1
                        else:
                            resolved += 1

    # Per-r3-action width from directly skipped subtrees/opponent branches.
    action_width: dict[
        tuple[TwoRoundInfoSet, NormalPlacementAction], float
    ] = {
        key: mass * utility_range for key, mass in direct_mass.items()
    }

    # Responding-first r4 infosets contribute at most the largest own-action
    # unresolved mass times Delta_u.  Their parent is one exact r3 own action.
    for info, masses in r4_skipped_mass.items():
        child_width = max(masses.values(), default=0.0) * utility_range
        parent = r4_parent[info]
        action_width[parent] = action_width.get(parent, 0.0) + child_width

    # At each responding-player r3 infoset, max over own actions cannot expand
    # uncertainty by more than the largest action-value width.
    by_info: dict[TwoRoundInfoSet, list[float]] = {}
    for info, actions in game.info_actions.items():
        if info.player != player or info.round_index != 3:
            continue
        widths = [action_width.get((info, action), 0.0) for action in actions]
        by_info[info] = widths
    width_cap = sum(max(widths, default=0.0) for widths in by_info.values())
    return _ThresholdSummary(
        threshold=float(threshold),
        width_cap=float(width_cap),
        resolved=resolved,
        skipped=skipped,
    )


def plan_target_width_budget(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    player: int,
    *,
    utility_range: float,
    target_width: float,
) -> TargetWidthBudgetPlan:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    delta = _finite(utility_range, "utility_range")
    target = _finite(target_width, "target_width")
    if delta < 0.0 or target < 0.0:
        raise ValueError("utility_range and target_width must be non-negative")

    thresholds = _enumerate_reach_thresholds(game, profile, player)
    summaries = [
        _summary_for_threshold(
            game,
            profile,
            player,
            utility_range=delta,
            threshold=threshold,
        )
        for threshold in thresholds
    ]
    feasible = [summary for summary in summaries if summary.width_cap <= target + 1e-12]
    if not feasible:
        raise AssertionError("zero-threshold M5R-F plan must always be feasible")
    # Larger threshold means a superset of pruned branches in this family.  Use
    # resolved work as a defensive tie-breaker against floating duplicate reaches.
    selected = max(feasible, key=lambda row: (row.threshold, -row.resolved))
    total = selected.resolved + selected.skipped
    if total <= 0:
        raise AssertionError("M5R-F planned no terminal histories")
    return TargetWidthBudgetPlan(
        player=player,
        target_width=target,
        selected_prune_reach_threshold=selected.threshold,
        guaranteed_unresolved_br_width_cap=selected.width_cap,
        utility_range=delta,
        planned_resolved_terminal_histories=selected.resolved,
        planned_skipped_terminal_histories=selected.skipped,
        total_terminal_histories=total,
        planned_terminal_work_fraction=selected.resolved / total,
        candidate_threshold_count=len(summaries),
        feasible_candidate_count=len(feasible),
    )
