from __future__ import annotations

"""Non-certifying held-out challenger screen for Normal/Fantasy routes."""

from dataclasses import dataclass
import hashlib
import json
import random
from typing import Mapping, Sequence

from fantasy_fantasy_payoff import continuation_fingerprint
from hu_continuation import HUContinuationState, KERNEL_NORMAL_FANTASY, hand_kernel_kind
from m5a_normal_fantasy_oracle import (
    NormalFantasyFixedPolicyOracle,
    model_fingerprint,
    policy_for_visible_node,
)
from m5h_normal_heldout_evidence import HeldoutNormalSeedMetric
from normal_fantasy_kernel import (
    NormalFantasyDealPlan,
    NormalFantasyState,
    child_normal_state,
    players_for_meta,
    sample_normal_fantasy_plan,
)
from normal_fantasy_symmetry import canonical_node_view

SCHEMA = "openofc-m5k-normal-fantasy-screening-v1"
AUTHORITY = "NORMAL_FANTASY_CHALLENGER_LOWER_BOUND_SCREENING_ONLY"
MASK64 = (1 << 64) - 1


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
        if target < cumulative:
            return index
    return len(probabilities) - 1


def _mean(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("M5K mean requires values")
    return float(sum(values) / len(values))


def _normal_gain_from_p0(
    normal_player: int,
    candidate_p0: float,
    challenger_p0: float,
) -> float:
    if normal_player == 0:
        return max(0.0, float(challenger_p0) - float(candidate_p0))
    if normal_player == 1:
        return max(0.0, float(candidate_p0) - float(challenger_p0))
    raise ValueError("persistent Normal player must be P0 or P1")


@dataclass(frozen=True)
class HeldoutSeedSpec:
    seed_id: str
    seed: int

    def __post_init__(self) -> None:
        if not str(self.seed_id).strip():
            raise ValueError("M5K held-out seed id must be non-empty")


@dataclass(frozen=True)
class NormalFantasyScreeningConfig:
    heldout_samples_per_seed: int = 128
    base_seed: int = 20260827

    def __post_init__(self) -> None:
        if self.heldout_samples_per_seed <= 0:
            raise ValueError("M5K held-out sample budget must be positive")

    def payload(self) -> dict[str, object]:
        return {
            "schema": "openofc-m5k-normal-fantasy-screening-config-v1",
            "heldout_samples_per_seed": int(self.heldout_samples_per_seed),
            "base_seed": int(self.base_seed) & MASK64,
        }

    @property
    def sha256(self) -> str:
        return _sha(self.payload())


@dataclass(frozen=True)
class NormalFantasyScreeningReport:
    state: str
    continuation_sha256: str
    candidate_oracle_id: str
    candidate_snapshot_sha256: str
    challenger_oracle_id: str
    challenger_snapshot_sha256: str
    terminal_evaluator_id: str
    config_sha256: str
    seed_metrics: tuple[HeldoutNormalSeedMetric, ...]
    normal_player: int
    max_observed_deviation_gain: float
    provenance: str
    sha256: str
    schema: str = SCHEMA
    authority: str = AUTHORITY
    certification_eligible: bool = False


def _rollout_on_plan(
    oracle: NormalFantasyFixedPolicyOracle,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    plan: NormalFantasyDealPlan,
    action_rng: random.Random,
    terminal_evaluator,
) -> float:
    normal_player, _fantasy_player = players_for_meta(state)
    node = NormalFantasyState(current_meta=state, plan=plan)
    while not node.terminal():
        key, pairs, _suit_map = canonical_node_view(node)
        action_keys = tuple(action_key for action_key, _action in pairs)
        probabilities = policy_for_visible_node(
            oracle.model, key, action_keys
        )
        selected = _sample_index(probabilities, action_rng)
        node = child_normal_state(node, pairs[selected][1])
    terminal = terminal_evaluator.evaluate(node, continuation_values)
    normal_value = float(terminal.utility_for_normal)
    return normal_value if normal_player == 0 else -normal_value


def screen_normal_fantasy_candidate(
    candidate: NormalFantasyFixedPolicyOracle,
    challenger: NormalFantasyFixedPolicyOracle,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    heldout_seeds: Sequence[HeldoutSeedSpec],
    config: NormalFantasyScreeningConfig = NormalFantasyScreeningConfig(),
    *,
    terminal_evaluator,
    terminal_evaluator_id: str,
    provenance: str,
) -> NormalFantasyScreeningReport:
    if hand_kernel_kind(state) != KERNEL_NORMAL_FANTASY:
        raise ValueError("M5K screening only supports Normal/Fantasy states")
    if not isinstance(candidate, NormalFantasyFixedPolicyOracle):
        raise TypeError("M5K candidate must be a frozen M5A NormalFantasyFixedPolicyOracle")
    if not isinstance(challenger, NormalFantasyFixedPolicyOracle):
        raise TypeError("M5K challenger must be a frozen M5A NormalFantasyFixedPolicyOracle")
    if model_fingerprint(candidate.model) != candidate.snapshot.model_sha256:
        raise ValueError("M5K candidate model/snapshot identity mismatch")
    if model_fingerprint(challenger.model) != challenger.snapshot.model_sha256:
        raise ValueError("M5K challenger model/snapshot identity mismatch")

    checked, continuation_sha = continuation_fingerprint(continuation_values)
    if candidate.snapshot.training_continuation_sha256 != continuation_sha:
        raise ValueError("M5K candidate snapshot is stale for the screened continuation vector")
    if challenger.snapshot.training_continuation_sha256 != continuation_sha:
        raise ValueError("M5K challenger snapshot is stale for the screened continuation vector")

    terminal_id = str(terminal_evaluator_id).strip()
    if not terminal_id:
        raise ValueError("M5K terminal evaluator id must be non-empty")
    if terminal_evaluator is None or not hasattr(terminal_evaluator, "evaluate"):
        raise TypeError("M5K terminal evaluator must expose evaluate()")
    provenance_text = str(provenance).strip()
    if not provenance_text:
        raise ValueError("M5K screening provenance must be non-empty")

    specs = tuple(heldout_seeds)
    if len(specs) < 2:
        raise ValueError("M5K real screening requires at least two held-out seeds")
    seed_ids = tuple(str(spec.seed_id) for spec in specs)
    if len(set(seed_ids)) != len(seed_ids):
        raise ValueError("M5K held-out seed ids must be unique")

    normal_player, fantasy_player = players_for_meta(state)
    fantasy_count = state.mode_for(fantasy_player)
    metrics: list[HeldoutNormalSeedMetric] = []
    for spec in sorted(specs, key=lambda row: str(row.seed_id)):
        chance_rng = random.Random(int(spec.seed) & MASK64)
        candidate_values: list[float] = []
        challenger_values: list[float] = []
        for sample_index in range(config.heldout_samples_per_seed):
            plan = sample_normal_fantasy_plan(chance_rng, fantasy_count)
            action_seed = _seed64(
                config.base_seed,
                spec.seed,
                sample_index,
                state.as_key(),
                "paired-actions",
            )
            candidate_values.append(
                _rollout_on_plan(
                    candidate,
                    state,
                    checked,
                    plan,
                    random.Random(action_seed),
                    terminal_evaluator,
                )
            )
            challenger_values.append(
                _rollout_on_plan(
                    challenger,
                    state,
                    checked,
                    plan,
                    random.Random(action_seed),
                    terminal_evaluator,
                )
            )

        candidate_p0 = _mean(candidate_values)
        challenger_p0 = _mean(challenger_values)
        gain = _normal_gain_from_p0(
            normal_player, candidate_p0, challenger_p0
        )
        metrics.append(
            HeldoutNormalSeedMetric(
                seed_id=str(spec.seed_id),
                samples=config.heldout_samples_per_seed,
                profile_p0_value=candidate_p0,
                p0_deviation_gain=gain if normal_player == 0 else None,
                p1_deviation_gain=gain if normal_player == 1 else None,
            )
        )

    max_gain = max(
        float(
            metric.p0_deviation_gain
            if normal_player == 0
            else metric.p1_deviation_gain
        )
        for metric in metrics
    )
    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "state": state.as_key(),
        "continuation_sha256": continuation_sha,
        "candidate_oracle_id": candidate.oracle_id,
        "candidate_snapshot_sha256": candidate.snapshot.sha256,
        "challenger_oracle_id": challenger.oracle_id,
        "challenger_snapshot_sha256": challenger.snapshot.sha256,
        "terminal_evaluator_id": terminal_id,
        "config_sha256": config.sha256,
        "seed_metrics": [
            {
                "seed_id": metric.seed_id,
                "samples": metric.samples,
                "profile_p0_value": metric.profile_p0_value,
                "p0_deviation_gain": metric.p0_deviation_gain,
                "p1_deviation_gain": metric.p1_deviation_gain,
            }
            for metric in metrics
        ],
        "normal_player": normal_player,
        "max_observed_deviation_gain": max_gain,
        "provenance": provenance_text,
        "certification_eligible": False,
    }
    return NormalFantasyScreeningReport(
        state=state.as_key(),
        continuation_sha256=continuation_sha,
        candidate_oracle_id=candidate.oracle_id,
        candidate_snapshot_sha256=candidate.snapshot.sha256,
        challenger_oracle_id=challenger.oracle_id,
        challenger_snapshot_sha256=challenger.snapshot.sha256,
        terminal_evaluator_id=terminal_id,
        config_sha256=config.sha256,
        seed_metrics=tuple(metrics),
        normal_player=normal_player,
        max_observed_deviation_gain=max_gain,
        provenance=provenance_text,
        sha256=_sha(payload),
    )
