from __future__ import annotations

"""Rigorous reduced-game best-response intervals from unresolved terminal mass."""

from dataclasses import dataclass
import hashlib
import math

from deepofc.actions import NormalPlacementAction
from deepofc.hu_two_round import HUTwoRoundSubgame, StrategyProfile, TwoRoundInfoSet
from deepofc.hu_two_round_br import exact_best_response

AUTHORITY = "RIGOROUS_TRUNCATED_REDUCED_BR_INTERVAL_NOT_ROUTE_CERTIFICATION"
SCHEMA = "openofc-m5r-truncated-reduced-br-interval-v1"


@dataclass
class _Interval:
    lower: float = 0.0
    upper: float = 0.0

    def add(self, lower: float, upper: float) -> None:
        if lower > upper + 1e-15:
            raise ValueError("invalid interval contribution")
        self.lower += float(lower)
        self.upper += float(upper)


@dataclass(frozen=True)
class TruncatedBRInterval:
    player: int
    resolution_modulus: int
    resolved_terminal_histories: int
    unresolved_terminal_histories: int
    zero_reach_terminal_histories: int
    lower_br_value: float
    upper_br_value: float
    exact_br_value: float
    lower_deviation_gain: float
    upper_deviation_gain: float
    exact_deviation_gain: float
    interval_width: float
    authority: str = AUTHORITY
    schema: str = SCHEMA
    production_certification_eligible: bool = False
    real_routes_certified: int = 0


def _terminal_selected(
    modulus: int,
    outcome,
    first_r3: NormalPlacementAction,
    second_r3: NormalPlacementAction,
    first_r4: NormalPlacementAction,
    second_r4: NormalPlacementAction,
) -> bool:
    if modulus <= 0:
        raise ValueError("resolution_modulus must be positive")
    if modulus == 1:
        return True
    token = "|".join(
        (
            repr(outcome),
            repr(first_r3.key()),
            repr(second_r3.key()),
            repr(first_r4.key()),
            repr(second_r4.key()),
        )
    ).encode("utf-8")
    value = int.from_bytes(hashlib.sha256(token).digest()[:8], "big")
    return value % modulus == 0


def truncated_best_response_interval(
    game: HUTwoRoundSubgame,
    profile: StrategyProfile,
    player: int,
    *,
    p0_utility_min: float,
    p0_utility_max: float,
    resolution_modulus: int,
) -> TruncatedBRInterval:
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    if resolution_modulus <= 0:
        raise ValueError("resolution_modulus must be positive")
    u0_min = float(p0_utility_min)
    u0_max = float(p0_utility_max)
    if not (math.isfinite(u0_min) and math.isfinite(u0_max) and u0_min <= u0_max):
        raise ValueError("utility interval must be finite and ordered")
    own_min, own_max = (
        (u0_min, u0_max) if player == 0 else (-u0_max, -u0_min)
    )

    cp = game.chance_probability
    round4_values: dict[
        TwoRoundInfoSet, dict[NormalPlacementAction, _Interval]
    ] = {}
    round4_parent: dict[
        TwoRoundInfoSet, tuple[TwoRoundInfoSet, NormalPlacementAction]
    ] = {}
    resolved = 0
    unresolved = 0
    zero_reach = 0

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
                first_r3_dist[first_r3]
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
                    second_r3_dist[second_r3]
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
                br_r3_info = (
                    first_r3_info if player == first else second_r3_info
                )
                br_own_r3 = (
                    first_own_r3 if player == first else second_own_r3
                )

                for first_r4 in first_r4_actions:
                    p_first_r4 = (
                        first_r4_dist[first_r4]
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
                    second_r4_dist = (
                        game._distribution(profile, second_r4_info)
                        if second != player
                        else None
                    )
                    br_r4_info = (
                        first_r4_info if player == first else second_r4_info
                    )
                    parent = (br_r3_info, br_own_r3)
                    previous = round4_parent.setdefault(br_r4_info, parent)
                    if previous != parent:
                        raise AssertionError("M5R-C perfect-recall predecessor mismatch")
                    bucket = round4_values.setdefault(
                        br_r4_info,
                        {action: _Interval() for action in game.actions(br_r4_info)},
                    )

                    for second_r4 in second_r4_actions:
                        p_second_r4 = (
                            second_r4_dist[second_r4]
                            if second_r4_dist is not None
                            else 1.0
                        )
                        own_r4 = (
                            first_r4 if player == first else second_r4
                        )
                        opponent_reach = (
                            cp
                            * p_first_r3
                            * p_second_r3
                            * p_first_r4
                            * p_second_r4
                        )
                        if opponent_reach <= 0.0:
                            zero_reach += 1
                            continue
                        if _terminal_selected(
                            resolution_modulus,
                            outcome,
                            first_r3,
                            second_r3,
                            first_r4,
                            second_r4,
                        ):
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
                            exact = opponent_reach * own_u
                            bucket[own_r4].add(exact, exact)
                            resolved += 1
                        else:
                            bucket[own_r4].add(
                                opponent_reach * own_min,
                                opponent_reach * own_max,
                            )
                            unresolved += 1

    round3_values: dict[
        TwoRoundInfoSet, dict[NormalPlacementAction, _Interval]
    ] = {}
    for info, action_intervals in round4_values.items():
        lower_best = max(interval.lower for interval in action_intervals.values())
        upper_best = max(interval.upper for interval in action_intervals.values())
        parent_info, parent_action = round4_parent[info]
        parent_bucket = round3_values.setdefault(
            parent_info,
            {action: _Interval() for action in game.actions(parent_info)},
        )
        parent_bucket[parent_action].add(lower_best, upper_best)

    lower_total = 0.0
    upper_total = 0.0
    for action_intervals in round3_values.values():
        lower_total += max(interval.lower for interval in action_intervals.values())
        upper_total += max(interval.upper for interval in action_intervals.values())

    exact = exact_best_response(game, profile, player).value
    if exact < lower_total - 1e-10 or exact > upper_total + 1e-10:
        raise AssertionError(
            f"M5R-C interval missed exact BR: lower={lower_total} exact={exact} upper={upper_total}"
        )
    profile_value_p0 = float(game.expected_u0(profile))
    own_profile_value = profile_value_p0 if player == 0 else -profile_value_p0
    lower_gain = lower_total - own_profile_value
    upper_gain = upper_total - own_profile_value
    exact_gain = float(exact) - own_profile_value
    if upper_gain + 1e-10 < exact_gain:
        raise AssertionError("M5R-C deviation upper bound fell below exact deviation")

    return TruncatedBRInterval(
        player=player,
        resolution_modulus=resolution_modulus,
        resolved_terminal_histories=resolved,
        unresolved_terminal_histories=unresolved,
        zero_reach_terminal_histories=zero_reach,
        lower_br_value=lower_total,
        upper_br_value=upper_total,
        exact_br_value=float(exact),
        lower_deviation_gain=lower_gain,
        upper_deviation_gain=upper_gain,
        exact_deviation_gain=exact_gain,
        interval_width=upper_total - lower_total,
    )
