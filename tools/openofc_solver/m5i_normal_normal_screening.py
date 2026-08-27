from __future__ import annotations

"""M5I learned-response exploit screening for the two Normal/Normal HU routes.

This module deliberately computes a *lower bound* on exploitable deviation gain:
it trains one visible-information response policy at a time against a frozen
candidate, then evaluates that learned response on independent held-out chance
seeds.  Finding a positive gain is valid fail-fast evidence that the candidate
is exploitable.  Failing to find a gain does not upper-bound exploitability and
can never certify a route.

The output is shaped for M5H `HELD_OUT_SCREENING_ONLY` evidence.
"""

from dataclasses import dataclass
import hashlib
import json
import math
import random
from typing import Mapping, Sequence

from fantasy_fantasy_payoff import continuation_fingerprint
from hu_continuation import (
    HUContinuationState,
    KERNEL_NORMAL_NORMAL,
    continuation_adjusted_terminal_utility,
    hand_kernel_kind,
    identity_for_role,
)
from m5a_normal_normal_oracle import (
    NormalNormalFixedPolicyOracle,
    model_fingerprint,
    policy_for_visible_node,
)
from m5h_normal_heldout_evidence import HeldoutNormalSeedMetric
from strategic_cfr import HUState, InfoSetNode, child_state, sample_deal_plan
from strategic_suit_symmetry import canonical_node_view

REPORT_SCHEMA = "openofc-m5i-normal-normal-screening-v1"
AUTHORITY = "LEARNED_RESPONSE_LOWER_BOUND_SCREENING_ONLY"
MASK64 = (1 << 64) - 1
EPS = 1e-12


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: Mapping[str, object]) -> str:
    raw = dict(payload)
    raw.pop("sha256", None)
    return hashlib.sha256(_canonical_bytes(raw)).hexdigest()


def _seed64(*parts: object) -> int:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") & MASK64


def _sample_index(probabilities: Sequence[float], rng: random.Random) -> int:
    if not probabilities:
        raise ValueError("cannot sample empty policy")
    target = rng.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        value = float(probability)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("invalid policy probability")
        cumulative += value
        if target < cumulative or index == len(probabilities) - 1:
            return index
    raise AssertionError("policy sampling fell through")


def _normalize(probabilities: Sequence[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in probabilities)
    if not values or any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("invalid policy probability vector")
    total = sum(values)
    if total <= 0.0:
        return tuple(1.0 / len(values) for _ in values)
    return tuple(value / total for value in values)


def _terminal_p0_value(
    meta: HUContinuationState,
    node: HUState,
    continuation_values: Mapping[HUContinuationState, float],
) -> float:
    if not node.terminal():
        raise ValueError("M5I terminal value requires a terminal HU state")
    persistent_boards = [None, None]
    for role in (0, 1):
        persistent = identity_for_role(meta, role)
        persistent_boards[persistent] = node.boards[role]
    if persistent_boards[0] is None or persistent_boards[1] is None:
        raise AssertionError("M5I persistent board remap failed")
    return float(
        continuation_adjusted_terminal_utility(
            meta,
            persistent_boards[0],
            persistent_boards[1],
            continuation_values,
            update_player=0,
        )
    )


@dataclass(frozen=True)
class HeldoutSeedSpec:
    seed_id: str
    seed: int

    def __post_init__(self) -> None:
        if not str(self.seed_id).strip():
            raise ValueError("M5I held-out seed id must be non-empty")


@dataclass(frozen=True)
class NormalNormalScreeningConfig:
    response_training_iterations: int = 256
    heldout_samples_per_seed: int = 128
    epsilon: float = 0.6
    base_seed: int = 20260827

    def __post_init__(self) -> None:
        if self.response_training_iterations <= 0 or self.heldout_samples_per_seed <= 0:
            raise ValueError("M5I budgets must be positive")
        if not 0.0 < float(self.epsilon) <= 1.0:
            raise ValueError("M5I epsilon must be in (0,1]")

    def payload(self) -> dict[str, object]:
        return {
            "response_training_iterations": int(self.response_training_iterations),
            "heldout_samples_per_seed": int(self.heldout_samples_per_seed),
            "epsilon": float(self.epsilon),
            "base_seed": int(self.base_seed) & MASK64,
        }

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True)
class DeviatorTrainingReport:
    persistent_player: int
    training_seed_id: str
    iterations: int
    infosets: int
    total_visits: int


@dataclass(frozen=True)
class NormalNormalScreeningReport:
    state: str
    continuation_sha256: str
    candidate_oracle_id: str
    candidate_model_sha256: str
    candidate_snapshot_sha256: str
    config_sha256: str
    response_training: tuple[DeviatorTrainingReport, ...]
    heldout_seed_ids: tuple[str, ...]
    heldout_samples_per_seed: int
    seed_metrics: tuple[HeldoutNormalSeedMetric, ...]
    max_p0_deviation_gain: float
    max_p1_deviation_gain: float
    max_observed_deviation_gain: float
    provenance: str
    sha256: str
    schema: str = REPORT_SCHEMA
    authority: str = AUTHORITY
    certification_eligible: bool = False


class LearnedResponsePolicy:
    """Outcome-sampling response learner against one frozen opponent policy."""

    def __init__(
        self,
        candidate: NormalNormalFixedPolicyOracle,
        meta: HUContinuationState,
        continuation_values: Mapping[HUContinuationState, float],
        *,
        deviator_player: int,
        epsilon: float,
        seed: int,
    ) -> None:
        if deviator_player not in (0, 1):
            raise ValueError("M5I deviator must be persistent player 0 or 1")
        if hand_kernel_kind(meta) != KERNEL_NORMAL_NORMAL:
            raise ValueError("M5I learner only supports Normal/Normal routes")
        if not 0.0 < float(epsilon) <= 1.0:
            raise ValueError("M5I epsilon must be in (0,1]")
        self.candidate = candidate
        self.meta = meta
        self.continuation_values = dict(continuation_values)
        self.deviator_player = int(deviator_player)
        self.epsilon = float(epsilon)
        self.seed = int(seed) & MASK64
        self.rng = random.Random(self.seed)
        self.nodes: dict[str, InfoSetNode] = {}
        self.iterations = 0

    def _node(self, key: str, action_keys: Sequence[str]) -> InfoSetNode:
        keys = tuple(action_keys)
        node = self.nodes.get(key)
        if node is None:
            node = InfoSetNode.create(keys)
            self.nodes[key] = node
        elif node.action_keys != keys:
            raise AssertionError("M5I infoset changed legal action set")
        return node

    def _candidate_policy(
        self, key: str, action_keys: Sequence[str]
    ) -> tuple[float, ...]:
        return _normalize(
            policy_for_visible_node(self.candidate.model, key, action_keys)
        )

    def _terminal_deviator_value(self, node: HUState) -> float:
        p0 = _terminal_p0_value(self.meta, node, self.continuation_values)
        return p0 if self.deviator_player == 0 else -p0

    def _episode(
        self,
        node_state: HUState,
        *,
        my_reach: float,
        opp_reach: float,
        sample_reach: float,
    ) -> float:
        if node_state.terminal():
            return self._terminal_deviator_value(node_state)

        key, pairs, _suit_map = canonical_node_view(node_state)
        action_keys = tuple(action_key for action_key, _action in pairs)
        actions = tuple(action for _action_key, action in pairs)
        persistent_actor = identity_for_role(self.meta, node_state.actor)
        is_deviator = persistent_actor == self.deviator_player

        if is_deviator:
            node = self._node(key, action_keys)
            target_policy = tuple(node.current_policy())
            uniform = 1.0 / len(target_policy)
            sample_policy = tuple(
                self.epsilon * uniform + (1.0 - self.epsilon) * probability
                for probability in target_policy
            )
        else:
            node = None
            target_policy = self._candidate_policy(key, action_keys)
            sample_policy = target_policy

        sampled = _sample_index(sample_policy, self.rng)
        if is_deviator:
            next_my_reach = my_reach * target_policy[sampled]
            next_opp_reach = opp_reach
        else:
            next_my_reach = my_reach
            next_opp_reach = opp_reach * target_policy[sampled]
        next_sample_reach = sample_reach * sample_policy[sampled]
        child_value = self._episode(
            child_state(node_state, actions[sampled]),
            my_reach=next_my_reach,
            opp_reach=next_opp_reach,
            sample_reach=next_sample_reach,
        )

        if not is_deviator:
            return child_value

        assert node is not None
        child_values = [0.0] * len(target_policy)
        child_values[sampled] = child_value / sample_policy[sampled]
        value_estimate = sum(
            target_policy[index] * child_values[index]
            for index in range(len(target_policy))
        )
        if sample_reach <= 0.0:
            raise AssertionError("M5I sample reach became non-positive")
        scale = opp_reach / sample_reach
        cf_value = value_estimate * scale
        for index in range(len(target_policy)):
            delta = child_values[index] * scale - cf_value
            node.cumulative_regrets[index] = max(
                0.0, node.cumulative_regrets[index] + delta
            )
            node.cumulative_policy[index] += (
                my_reach * target_policy[index] / sample_reach
            )
        node.visits += 1
        return value_estimate

    def run(self, iterations: int) -> DeviatorTrainingReport:
        if iterations <= 0:
            raise ValueError("M5I response training iterations must be positive")
        for _ in range(iterations):
            root = HUState(plan=sample_deal_plan(self.rng))
            self._episode(
                root,
                my_reach=1.0,
                opp_reach=1.0,
                sample_reach=1.0,
            )
            self.iterations += 1
        return DeviatorTrainingReport(
            persistent_player=self.deviator_player,
            training_seed_id=f"m5i-response-train-p{self.deviator_player}:{self.seed}",
            iterations=self.iterations,
            infosets=len(self.nodes),
            total_visits=sum(node.visits for node in self.nodes.values()),
        )

    def average_policy_for_visible_node(
        self, key: str, action_keys: Sequence[str]
    ) -> tuple[float, ...]:
        keys = tuple(action_keys)
        node = self.nodes.get(key)
        if node is None:
            return tuple(1.0 / len(keys) for _ in keys)
        if node.action_keys != keys:
            raise AssertionError("M5I evaluation infoset action set drifted")
        return _normalize(node.average_policy())


def _rollout_profile(
    candidate: NormalNormalFixedPolicyOracle,
    meta: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    plan,
    rng: random.Random,
    *,
    response: LearnedResponsePolicy | None = None,
) -> float:
    node = HUState(plan=plan)
    while not node.terminal():
        key, pairs, _suit_map = canonical_node_view(node)
        action_keys = tuple(action_key for action_key, _action in pairs)
        persistent_actor = identity_for_role(meta, node.actor)
        if response is not None and persistent_actor == response.deviator_player:
            probabilities = response.average_policy_for_visible_node(key, action_keys)
        else:
            probabilities = _normalize(
                policy_for_visible_node(candidate.model, key, action_keys)
            )
        selected = _sample_index(probabilities, rng)
        node = child_state(node, pairs[selected][1])
    return _terminal_p0_value(meta, node, continuation_values)


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("M5I mean requires values")
    return float(sum(values) / len(values))


def screen_normal_normal_candidate(
    candidate: NormalNormalFixedPolicyOracle,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    heldout_seeds: Sequence[HeldoutSeedSpec],
    config: NormalNormalScreeningConfig = NormalNormalScreeningConfig(),
    *,
    provenance: str,
) -> NormalNormalScreeningReport:
    """Train two unilateral learned responses and score them on held-out seeds."""
    if hand_kernel_kind(state) != KERNEL_NORMAL_NORMAL:
        raise ValueError("M5I screening only supports Normal/Normal states")
    if not isinstance(candidate, NormalNormalFixedPolicyOracle):
        raise TypeError("M5I candidate must be a frozen M5A NormalNormalFixedPolicyOracle")
    if model_fingerprint(candidate.model) != candidate.snapshot.model_sha256:
        raise ValueError("M5I candidate model/snapshot identity mismatch")
    seed_specs = tuple(heldout_seeds)
    if len(seed_specs) < 2:
        raise ValueError("M5I real screening requires at least two held-out seeds")
    seed_ids = tuple(str(spec.seed_id) for spec in seed_specs)
    if len(set(seed_ids)) != len(seed_ids):
        raise ValueError("M5I held-out seed ids must be unique")
    provenance_text = str(provenance).strip()
    if not provenance_text:
        raise ValueError("M5I screening provenance must be non-empty")

    checked, continuation_sha = continuation_fingerprint(continuation_values)
    responses: dict[int, LearnedResponsePolicy] = {}
    training_reports: list[DeviatorTrainingReport] = []
    for player in (0, 1):
        seed = _seed64(config.base_seed, state.as_key(), "response-train", player)
        learner = LearnedResponsePolicy(
            candidate,
            state,
            checked,
            deviator_player=player,
            epsilon=config.epsilon,
            seed=seed,
        )
        training_reports.append(learner.run(config.response_training_iterations))
        responses[player] = learner

    metrics: list[HeldoutNormalSeedMetric] = []
    for spec in sorted(seed_specs, key=lambda row: str(row.seed_id)):
        chance_rng = random.Random(int(spec.seed) & MASK64)
        baseline_values: list[float] = []
        p0_response_values: list[float] = []
        p1_response_values: list[float] = []
        for sample_index in range(config.heldout_samples_per_seed):
            plan = sample_deal_plan(chance_rng)
            baseline_values.append(
                _rollout_profile(
                    candidate,
                    state,
                    checked,
                    plan,
                    random.Random(
                        _seed64(spec.seed, sample_index, "candidate-profile")
                    ),
                )
            )
            p0_response_values.append(
                _rollout_profile(
                    candidate,
                    state,
                    checked,
                    plan,
                    random.Random(_seed64(spec.seed, sample_index, "p0-response")),
                    response=responses[0],
                )
            )
            p1_response_values.append(
                _rollout_profile(
                    candidate,
                    state,
                    checked,
                    plan,
                    random.Random(_seed64(spec.seed, sample_index, "p1-response")),
                    response=responses[1],
                )
            )

        baseline_p0 = _mean(baseline_values)
        p0_gain = max(0.0, _mean(p0_response_values) - baseline_p0)
        # Persistent P1 utility is -P0. A lower P0 value is therefore a P1 gain.
        p1_gain = max(0.0, baseline_p0 - _mean(p1_response_values))
        metrics.append(
            HeldoutNormalSeedMetric(
                seed_id=str(spec.seed_id),
                samples=config.heldout_samples_per_seed,
                profile_p0_value=baseline_p0,
                p0_deviation_gain=p0_gain,
                p1_deviation_gain=p1_gain,
            )
        )

    p0_max = max(float(row.p0_deviation_gain or 0.0) for row in metrics)
    p1_max = max(float(row.p1_deviation_gain or 0.0) for row in metrics)
    payload: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "authority": AUTHORITY,
        "state": state.as_key(),
        "continuation_sha256": continuation_sha,
        "candidate_oracle_id": candidate.oracle_id,
        "candidate_model_sha256": candidate.snapshot.model_sha256,
        "candidate_snapshot_sha256": candidate.snapshot.sha256,
        "config_sha256": config.sha256,
        "response_training": [
            {
                "persistent_player": row.persistent_player,
                "training_seed_id": row.training_seed_id,
                "iterations": row.iterations,
                "infosets": row.infosets,
                "total_visits": row.total_visits,
            }
            for row in training_reports
        ],
        "heldout_seed_ids": [row.seed_id for row in metrics],
        "heldout_samples_per_seed": config.heldout_samples_per_seed,
        "seed_metrics": [
            {
                "seed_id": row.seed_id,
                "samples": row.samples,
                "profile_p0_value": row.profile_p0_value,
                "p0_deviation_gain": row.p0_deviation_gain,
                "p1_deviation_gain": row.p1_deviation_gain,
            }
            for row in metrics
        ],
        "max_p0_deviation_gain": p0_max,
        "max_p1_deviation_gain": p1_max,
        "max_observed_deviation_gain": max(p0_max, p1_max),
        "provenance": provenance_text,
        "certification_eligible": False,
    }
    report_sha = _sha(payload)
    return NormalNormalScreeningReport(
        state=state.as_key(),
        continuation_sha256=continuation_sha,
        candidate_oracle_id=candidate.oracle_id,
        candidate_model_sha256=candidate.snapshot.model_sha256,
        candidate_snapshot_sha256=candidate.snapshot.sha256,
        config_sha256=config.sha256,
        response_training=tuple(training_reports),
        heldout_seed_ids=tuple(row.seed_id for row in metrics),
        heldout_samples_per_seed=config.heldout_samples_per_seed,
        seed_metrics=tuple(metrics),
        max_p0_deviation_gain=p0_max,
        max_p1_deviation_gain=p1_max,
        max_observed_deviation_gain=max(p0_max, p1_max),
        provenance=provenance_text,
        sha256=report_sha,
    )
