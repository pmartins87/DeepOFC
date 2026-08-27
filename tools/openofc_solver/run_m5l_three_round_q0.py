from __future__ import annotations

"""M5L Q0: qualify response-search mechanics against exact three-round BR.

This is a calibration diagnostic only.  It does not create a certification-
eligible M5H reference evaluator manifest.
"""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Mapping, Sequence

from deepofc.actions import NormalPlacementAction
from deepofc.hu_three_round_br import (
    ThreeRoundBestResponse,
    exact_best_response,
    exact_value_of_pure_response,
)
from deepofc.hu_three_round_sequential import (
    HUThreeRoundSequentialSubgame,
    StrategyProfile,
)
from deepofc.sequential import HUPlayerObservation, HUSequentialNormalState

SCHEMA = "openofc-m5l-three-round-q0-v1"
AUTHORITY = "QUALIFICATION_DIAGNOSTIC_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5l_three_round_q0.json"
BUDGETS = (64, 256, 1024)
EPSILON = 0.6
BASE_SEED = 2026082751
TOL = 1e-9


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _seed64(*parts: object) -> int:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _sample_index(probabilities: Sequence[float], rng: random.Random) -> int:
    target = rng.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += float(probability)
        if target < cumulative or index == len(probabilities) - 1:
            return index
    raise AssertionError("M5L policy sampling fell through")


@dataclass
class _ResponseNode:
    actions: tuple[NormalPlacementAction, ...]
    regrets: list[float]
    cumulative_policy: list[float]
    visits: int = 0

    @classmethod
    def create(cls, actions: Sequence[NormalPlacementAction]) -> "_ResponseNode":
        frozen = tuple(actions)
        return cls(frozen, [0.0] * len(frozen), [0.0] * len(frozen))

    def current_policy(self) -> tuple[float, ...]:
        positive = [max(0.0, value) for value in self.regrets]
        total = sum(positive)
        if total <= 0.0:
            return tuple(1.0 / len(positive) for _ in positive)
        return tuple(value / total for value in positive)

    def average_policy(self) -> tuple[float, ...]:
        total = sum(self.cumulative_policy)
        if total <= 0.0:
            return self.current_policy()
        return tuple(value / total for value in self.cumulative_policy)


class OutcomeSampledResponseLearner:
    """Three-round analogue of the M5I unilateral outcome-sampling learner."""

    def __init__(
        self,
        game: HUThreeRoundSequentialSubgame,
        opponent_profile: StrategyProfile,
        *,
        deviator_player: int,
        epsilon: float,
        seed: int,
    ) -> None:
        if deviator_player not in (0, 1):
            raise ValueError("M5L deviator player must be 0 or 1")
        if not 0.0 < float(epsilon) <= 1.0:
            raise ValueError("M5L epsilon must be in (0,1]")
        self.game = game
        self.opponent_profile = opponent_profile
        self.deviator_player = int(deviator_player)
        self.epsilon = float(epsilon)
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.nodes: dict[HUPlayerObservation, _ResponseNode] = {}
        self.iterations = 0
        self.terminal_evaluations = 0

    def _node(self, info: HUPlayerObservation) -> _ResponseNode:
        actions = tuple(self.game.actions(info))
        node = self.nodes.get(info)
        if node is None:
            node = _ResponseNode.create(actions)
            self.nodes[info] = node
        elif node.actions != actions:
            raise AssertionError("M5L infoset legal actions changed")
        return node

    def _terminal_value(self, state: HUSequentialNormalState) -> float:
        self.terminal_evaluations += 1
        u0 = float(self.game.terminal_u0(state))
        return u0 if self.deviator_player == 0 else -u0

    def _episode(
        self,
        state: HUSequentialNormalState,
        *,
        my_reach: float,
        opp_reach: float,
        sample_reach: float,
    ) -> float:
        if state.terminal:
            return self._terminal_value(state)

        info = self.game.info(state)
        actions = tuple(self.game.actions(info))
        is_deviator = state.acting_chair == self.deviator_player
        if is_deviator:
            node = self._node(info)
            target = node.current_policy()
            uniform = 1.0 / len(target)
            sampling = tuple(
                self.epsilon * uniform + (1.0 - self.epsilon) * probability
                for probability in target
            )
        else:
            node = None
            distribution = self.game.distribution(self.opponent_profile, info)
            target = tuple(float(distribution[action]) for action in actions)
            sampling = target

        sampled = _sample_index(sampling, self.rng)
        if is_deviator:
            next_my = my_reach * target[sampled]
            next_opp = opp_reach
        else:
            next_my = my_reach
            next_opp = opp_reach * target[sampled]
        next_sample = sample_reach * sampling[sampled]
        child = self._episode(
            self.game.transition(state, actions[sampled]),
            my_reach=next_my,
            opp_reach=next_opp,
            sample_reach=next_sample,
        )
        if not is_deviator:
            return child

        assert node is not None
        sampled_probability = sampling[sampled]
        if sampled_probability <= 0.0 or sample_reach <= 0.0:
            raise AssertionError("M5L sample reach became non-positive")
        child_values = [0.0] * len(actions)
        child_values[sampled] = child / sampled_probability
        value_estimate = sum(
            target[index] * child_values[index]
            for index in range(len(actions))
        )
        scale = opp_reach / sample_reach
        cf_value = value_estimate * scale
        for index in range(len(actions)):
            delta = child_values[index] * scale - cf_value
            node.regrets[index] = max(0.0, node.regrets[index] + delta)
            node.cumulative_policy[index] += (
                my_reach * target[index] / sample_reach
            )
        node.visits += 1
        return value_estimate

    def step(self) -> None:
        outcome = self.game.outcomes[self.rng.randrange(len(self.game.outcomes))]
        self._episode(
            self.game.initial_state(outcome),
            my_reach=1.0,
            opp_reach=1.0,
            sample_reach=1.0,
        )
        self.iterations += 1

    def run_to(self, target_iterations: int) -> None:
        if target_iterations < self.iterations:
            raise ValueError("M5L cannot run backwards")
        while self.iterations < target_iterations:
            self.step()

    def pure_response(
        self,
        exact_reference: ThreeRoundBestResponse,
    ) -> tuple[ThreeRoundBestResponse, int, int]:
        choices: dict[HUPlayerObservation, NormalPlacementAction] = {}
        learned = 0
        fallback = 0
        for info in exact_reference.choices:
            actions = tuple(self.game.actions(info))
            node = self.nodes.get(info)
            if node is None:
                distribution = self.game.distribution(self.opponent_profile, info)
                best_probability = max(float(distribution[action]) for action in actions)
                eligible = [
                    action
                    for action in actions
                    if abs(float(distribution[action]) - best_probability) <= 1e-15
                ]
                chosen = min(eligible, key=lambda action: action.key())
                fallback += 1
            else:
                average = node.average_policy()
                best_probability = max(average)
                eligible = [
                    action
                    for action, probability in zip(actions, average)
                    if abs(probability - best_probability) <= 1e-15
                ]
                chosen = min(eligible, key=lambda action: action.key())
                learned += 1
            choices[info] = chosen
        return (
            ThreeRoundBestResponse(
                player=self.deviator_player,
                value=0.0,
                choices=choices,
                terminal_histories=0,
            ),
            learned,
            fallback,
        )


def _source_manifest() -> dict[str, object]:
    paths = (
        "deepofc/hu_three_round_br.py",
        "deepofc/hu_three_round_sequential.py",
        "tools/openofc_solver/M5L_REFERENCE_EVALUATOR_QUALIFICATION_CONTRACT.md",
        "tools/openofc_solver/run_m5l_three_round_q0.py",
    )
    rows = []
    for rel in paths:
        raw = (ROOT / rel).read_bytes()
        rows.append(
            {"path": rel, "sha256": hashlib.sha256(raw).hexdigest()}
        )
    payload: dict[str, object] = {"files": rows}
    payload["sha256"] = _sha(payload)
    return payload


def main() -> None:
    game = HUThreeRoundSequentialSubgame()
    opponent_profile: StrategyProfile = {}
    source_manifest = _source_manifest()
    rows: list[dict[str, object]] = []

    for player in (0, 1):
        exact = exact_best_response(game, opponent_profile, player)
        exact_replay, exact_replay_terminals = exact_value_of_pure_response(
            game, opponent_profile, exact
        )
        if abs(exact.value - exact_replay) > 1e-10:
            raise RuntimeError("M5L exact BR independent replay mismatch")

        learner = OutcomeSampledResponseLearner(
            game,
            opponent_profile,
            deviator_player=player,
            epsilon=EPSILON,
            seed=_seed64(BASE_SEED, "q0", player),
        )
        for budget in BUDGETS:
            learner.run_to(budget)
            response, learned_infosets, fallback_infosets = learner.pure_response(exact)
            approximate_value, replay_terminals = exact_value_of_pure_response(
                game, opponent_profile, response
            )
            residual = float(exact.value - approximate_value)
            if residual < -TOL:
                raise RuntimeError(
                    "M5L approximate response exceeded exact best response"
                )
            total_infosets = len(exact.choices)
            rows.append(
                {
                    "player": player,
                    "budget": budget,
                    "exact_best_response_value": float(exact.value),
                    "exact_best_response_infosets": total_infosets,
                    "exact_best_response_terminal_histories": exact.terminal_histories,
                    "exact_replay_value": float(exact_replay),
                    "exact_replay_terminals": exact_replay_terminals,
                    "approximate_pure_response_value": float(approximate_value),
                    "underestimation_residual": max(0.0, residual),
                    "learner_infosets_seen": len(learner.nodes),
                    "responding_infosets_learned": learned_infosets,
                    "responding_infosets_fallback": fallback_infosets,
                    "responding_infoset_coverage": (
                        learned_infosets / total_infosets if total_infosets else 1.0
                    ),
                    "learner_terminal_evaluations": learner.terminal_evaluations,
                    "pure_replay_terminals": replay_terminals,
                    "training_seed": learner.seed,
                }
            )

    if any(
        not math.isfinite(float(row["underestimation_residual"]))
        for row in rows
    ):
        raise RuntimeError("M5L produced non-finite residual")

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "qualification_stage": "Q0_PIPELINE_SMOKE",
        "candidate_profile": "UNIFORM",
        "budgets": list(BUDGETS),
        "epsilon": EPSILON,
        "base_seed": BASE_SEED,
        "source_manifest": source_manifest,
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "players": [0, 1],
            "max_underestimation_residual": max(
                float(row["underestimation_residual"]) for row in rows
            ),
            "min_underestimation_residual": min(
                float(row["underestimation_residual"]) for row in rows
            ),
            "certification_eligible": False,
            "reference_manifest_emitted": False,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "artifact": str(OUT.relative_to(ROOT)),
                "sha256": payload["sha256"],
                "rows": rows,
                "certification_eligible": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
