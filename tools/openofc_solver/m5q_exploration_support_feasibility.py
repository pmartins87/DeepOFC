from __future__ import annotations

"""Structural support floor for hypothetical exploration-mixed External Sampling.

This module does not modify the production solver.  It computes the guaranteed
terminal-history sampling floor that *would* hold if every sampled local policy
were mixed with uniform exploration mass epsilon.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import math

from deepofc.hu_two_round import HUTwoRoundSubgame

SCHEMA = "openofc-m5q-exploration-support-feasibility-v1"
AUTHORITY = "EXPLORATION_SUPPORTED_EXTERNAL_SAMPLING_FEASIBILITY_NOT_CERTIFICATION"


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class TraverserExplorationSupport:
    traverser: int
    epsilon: float
    terminal_histories: int
    minimum_structural_sampling_probability: float
    maximum_sampled_decisions: int
    maximum_sampled_action_count: int

    def payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExplorationSupportReport:
    epsilon: float
    player0: TraverserExplorationSupport
    player1: TraverserExplorationSupport
    global_sampling_probability_floor: float
    authority: str = AUTHORITY
    schema: str = SCHEMA
    sha256: str = ""

    def unsigned_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "epsilon": self.epsilon,
            "player0": self.player0.payload(),
            "player1": self.player1.payload(),
            "global_sampling_probability_floor": self.global_sampling_probability_floor,
            "production_solver_modified": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        }

    def payload(self) -> dict[str, object]:
        payload = self.unsigned_payload()
        payload["sha256"] = self.sha256
        return payload


def _local_floor(epsilon: float, action_count: int) -> float:
    if action_count <= 0:
        raise ValueError("M5Q exploration support encountered an empty action set")
    return epsilon / float(action_count)


def exploration_structural_support_report(
    game: HUTwoRoundSubgame,
    epsilon: float,
) -> ExplorationSupportReport:
    """Compute exact structural lower support for the two-round benchmark.

    Chance is sampled uniformly.  The traverser's decisions are enumerated by
    External Sampling and do not contribute to q_i(z).  Each opponent decision
    contributes epsilon / |A(I)|, the minimum guaranteed by uniform mixing.
    """

    eps = float(epsilon)
    if not math.isfinite(eps) or not (0.0 < eps <= 1.0):
        raise ValueError("epsilon must be finite and in (0,1]")
    cp = float(game.chance_probability)
    if not math.isfinite(cp) or cp <= 0.0:
        raise ValueError("chance probability must be finite and positive")

    counts = [0, 0]
    minima = [math.inf, math.inf]
    max_sampled_decisions = [0, 0]
    max_sampled_action_count = [0, 0]

    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player

        first_r3_info = game.round3_first_info(outcome)
        first_r3_actions = game.actions(first_r3_info)
        for first_r3 in first_r3_actions:
            second_r3_info = game.round3_second_info(outcome, first_r3)
            second_r3_actions = game.actions(second_r3_info)
            for second_r3 in second_r3_actions:
                _, _, action0_r3, action1_r3 = game._boards_after_round3(
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
                for first_r4 in first_r4_actions:
                    second_r4_info = game.round4_info(
                        outcome,
                        player=second,
                        own_round3_action=second_own_r3,
                        opponent_round3_action=second_opp_r3,
                        current_first_action=first_r4,
                    )
                    second_r4_actions = game.actions(second_r4_info)
                    for _second_r4 in second_r4_actions:
                        infos = (
                            (first, first_r3_info),
                            (second, second_r3_info),
                            (first, first_r4_info),
                            (second, second_r4_info),
                        )
                        for traverser in (0, 1):
                            q = cp
                            sampled_decisions = 0
                            local_max_actions = 0
                            for actor, info in infos:
                                if actor == traverser:
                                    continue
                                action_count = len(game.actions(info))
                                q *= _local_floor(eps, action_count)
                                sampled_decisions += 1
                                local_max_actions = max(local_max_actions, action_count)
                            counts[traverser] += 1
                            minima[traverser] = min(minima[traverser], q)
                            max_sampled_decisions[traverser] = max(
                                max_sampled_decisions[traverser], sampled_decisions
                            )
                            max_sampled_action_count[traverser] = max(
                                max_sampled_action_count[traverser], local_max_actions
                            )

    rows: list[TraverserExplorationSupport] = []
    for traverser in (0, 1):
        if counts[traverser] <= 0 or not math.isfinite(minima[traverser]):
            raise RuntimeError("M5Q exploration support found no terminal histories")
        if minima[traverser] <= 0.0:
            raise AssertionError("positive exploration must imply positive support")
        rows.append(
            TraverserExplorationSupport(
                traverser=traverser,
                epsilon=eps,
                terminal_histories=counts[traverser],
                minimum_structural_sampling_probability=float(minima[traverser]),
                maximum_sampled_decisions=max_sampled_decisions[traverser],
                maximum_sampled_action_count=max_sampled_action_count[traverser],
            )
        )

    global_floor = min(
        rows[0].minimum_structural_sampling_probability,
        rows[1].minimum_structural_sampling_probability,
    )
    unsigned: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "epsilon": eps,
        "player0": rows[0].payload(),
        "player1": rows[1].payload(),
        "global_sampling_probability_floor": global_floor,
        "production_solver_modified": False,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    return ExplorationSupportReport(
        epsilon=eps,
        player0=rows[0],
        player1=rows[1],
        global_sampling_probability_floor=global_floor,
        sha256=_sha(unsigned),
    )
