from __future__ import annotations

"""Paired-uncertainty challenger screening for Normal/Fantasy routes.

M5N remains a non-certifying lower-bound diagnostic.  It strengthens M5K by
retaining per-deal paired differences and uncertainty instead of comparing only
separate candidate/challenger means.
"""

from dataclasses import dataclass
import hashlib
import json
import math
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
from m5k_normal_fantasy_screening import HeldoutSeedSpec
from normal_fantasy_kernel import (
    NormalFantasyDealPlan,
    NormalFantasyState,
    child_normal_state,
    players_for_meta,
    sample_normal_fantasy_plan,
)
from normal_fantasy_symmetry import canonical_node_view

CONFIG_SCHEMA = "openofc-m5n-normal-fantasy-paired-config-v1"
REPORT_SCHEMA = "openofc-m5n-normal-fantasy-paired-screening-v1"
AUTHORITY = "NORMAL_FANTASY_PAIRED_UNCERTAINTY_SCREENING_ONLY"
MASK64 = (1 << 64) - 1


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _seed64(*parts: object) -> int:
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") & MASK64


def _sample_index(probabilities: Sequence[float], rng: random.Random) -> int:
    if not probabilities:
        raise ValueError("M5N cannot sample an empty policy")
    target = rng.random()
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        value = float(probability)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("M5N policy contains an invalid probability")
        cumulative += value
        if target < cumulative or index == len(probabilities) - 1:
            return index
    raise AssertionError("M5N policy sampling fell through")


def _mean_se(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        raise ValueError("M5N mean/SE requires observations")
    mean = float(sum(float(x) for x in values) / len(values))
    if len(values) == 1:
        return mean, 0.0
    variance = sum((float(x) - mean) ** 2 for x in values) / (len(values) - 1)
    return mean, float(math.sqrt(max(0.0, variance) / len(values)))


def _signed_normal_gain(
    normal_player: int,
    candidate_p0: float,
    challenger_p0: float,
) -> float:
    if normal_player == 0:
        return float(challenger_p0) - float(candidate_p0)
    if normal_player == 1:
        return float(candidate_p0) - float(challenger_p0)
    raise ValueError("persistent Normal player must be P0 or P1")


@dataclass(frozen=True)
class PairedNormalFantasyConfig:
    heldout_samples_per_seed: int = 128
    confidence_multiplier: float = 3.182
    base_seed: int = 2026082961

    def __post_init__(self) -> None:
        if self.heldout_samples_per_seed <= 0:
            raise ValueError("M5N held-out sample budget must be positive")
        if not math.isfinite(self.confidence_multiplier) or self.confidence_multiplier <= 0.0:
            raise ValueError("M5N confidence multiplier must be positive and finite")

    def payload(self) -> dict[str, object]:
        return {
            "schema": CONFIG_SCHEMA,
            "heldout_samples_per_seed": int(self.heldout_samples_per_seed),
            "confidence_multiplier": float(self.confidence_multiplier),
            "base_seed": int(self.base_seed) & MASK64,
        }

    @property
    def sha256(self) -> str:
        return _sha(self.payload())


@dataclass(frozen=True)
class PairedNormalFantasySeedMetric:
    seed_id: str
    samples: int
    profile_p0_value: float
    profile_value_standard_error: float
    signed_normal_gain: float
    gain_standard_error: float
    normal_player: int

    def as_m5h_diagnostic(self) -> HeldoutNormalSeedMetric:
        gain = max(0.0, float(self.signed_normal_gain))
        return HeldoutNormalSeedMetric(
            seed_id=self.seed_id,
            samples=self.samples,
            profile_p0_value=self.profile_p0_value,
            p0_deviation_gain=gain if self.normal_player == 0 else None,
            p1_deviation_gain=gain if self.normal_player == 1 else None,
        )


@dataclass(frozen=True)
class PairedNormalFantasyAggregate:
    normal_player: int
    seed_mean_signed_gain: float
    seed_standard_error: float
    confidence_multiplier: float
    conservative_lower_signal: float


@dataclass(frozen=True)
class PairedNormalFantasyScreeningReport:
    state: str
    continuation_sha256: str
    candidate_oracle_id: str
    candidate_snapshot_sha256: str
    challenger_oracle_id: str
    challenger_snapshot_sha256: str
    terminal_evaluator_id: str
    config_sha256: str
    normal_player: int
    heldout_seed_ids: tuple[str, ...]
    heldout_samples_per_seed: int
    paired_seed_metrics: tuple[PairedNormalFantasySeedMetric, ...]
    aggregate: PairedNormalFantasyAggregate
    max_conservative_deviation_signal: float
    provenance: str
    sha256: str
    schema: str = REPORT_SCHEMA
    authority: str = AUTHORITY
    certification_eligible: bool = False


def _rollout_on_plan(
    oracle: NormalFantasyFixedPolicyOracle,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    plan: NormalFantasyDealPlan,
    *,
    policy_seed: int,
    terminal_evaluator,
) -> float:
    normal_player, _fantasy_player = players_for_meta(state)
    rng = random.Random(int(policy_seed) & MASK64)
    node = NormalFantasyState(current_meta=state, plan=plan)
    while not node.terminal():
        key, pairs, _suit_map = canonical_node_view(node)
        action_keys = tuple(action_key for action_key, _action in pairs)
        probabilities = policy_for_visible_node(oracle.model, key, action_keys)
        selected = _sample_index(probabilities, rng)
        node = child_normal_state(node, pairs[selected][1])
    terminal = terminal_evaluator.evaluate(node, continuation_values)
    normal_value = float(terminal.utility_for_normal)
    return normal_value if normal_player == 0 else -normal_value


def screen_paired_normal_fantasy_candidate(
    candidate: NormalFantasyFixedPolicyOracle,
    challenger: NormalFantasyFixedPolicyOracle,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    heldout_seeds: Sequence[HeldoutSeedSpec],
    config: PairedNormalFantasyConfig = PairedNormalFantasyConfig(),
    *,
    terminal_evaluator,
    terminal_evaluator_id: str,
    provenance: str,
) -> PairedNormalFantasyScreeningReport:
    if hand_kernel_kind(state) != KERNEL_NORMAL_FANTASY:
        raise ValueError("M5N screening only supports Normal/Fantasy states")
    if not isinstance(candidate, NormalFantasyFixedPolicyOracle):
        raise TypeError("M5N candidate must be a frozen NormalFantasyFixedPolicyOracle")
    if not isinstance(challenger, NormalFantasyFixedPolicyOracle):
        raise TypeError("M5N challenger must be a frozen NormalFantasyFixedPolicyOracle")
    if model_fingerprint(candidate.model) != candidate.snapshot.model_sha256:
        raise ValueError("M5N candidate model/snapshot identity mismatch")
    if model_fingerprint(challenger.model) != challenger.snapshot.model_sha256:
        raise ValueError("M5N challenger model/snapshot identity mismatch")

    checked, continuation_sha = continuation_fingerprint(continuation_values)
    if candidate.snapshot.training_continuation_sha256 != continuation_sha:
        raise ValueError("M5N candidate snapshot is stale for the screened continuation vector")
    if challenger.snapshot.training_continuation_sha256 != continuation_sha:
        raise ValueError("M5N challenger snapshot is stale for the screened continuation vector")

    terminal_id = str(terminal_evaluator_id).strip()
    if not terminal_id:
        raise ValueError("M5N terminal evaluator id must be non-empty")
    if terminal_evaluator is None or not hasattr(terminal_evaluator, "evaluate"):
        raise TypeError("M5N terminal evaluator must expose evaluate()")
    provenance_text = str(provenance).strip()
    if not provenance_text:
        raise ValueError("M5N provenance must be non-empty")

    specs = tuple(heldout_seeds)
    if len(specs) < 4:
        raise ValueError("M5N requires at least four held-out seed identities")
    seed_ids = tuple(str(spec.seed_id) for spec in specs)
    if any(not seed_id.strip() for seed_id in seed_ids):
        raise ValueError("M5N held-out seed ids must be non-empty")
    if len(set(seed_ids)) != len(seed_ids):
        raise ValueError("M5N held-out seed ids must be unique")

    normal_player, fantasy_player = players_for_meta(state)
    fantasy_count = state.mode_for(fantasy_player)
    metrics: list[PairedNormalFantasySeedMetric] = []
    for spec in sorted(specs, key=lambda row: str(row.seed_id)):
        chance_rng = random.Random(int(spec.seed) & MASK64)
        candidate_values: list[float] = []
        paired_gains: list[float] = []
        for sample_index in range(config.heldout_samples_per_seed):
            plan = sample_normal_fantasy_plan(chance_rng, fantasy_count)
            paired_seed = _seed64(
                config.base_seed,
                spec.seed,
                sample_index,
                state.as_key(),
                "m5n-paired-policy",
            )
            candidate_p0 = _rollout_on_plan(
                candidate,
                state,
                checked,
                plan,
                policy_seed=paired_seed,
                terminal_evaluator=terminal_evaluator,
            )
            challenger_p0 = _rollout_on_plan(
                challenger,
                state,
                checked,
                plan,
                policy_seed=paired_seed,
                terminal_evaluator=terminal_evaluator,
            )
            candidate_values.append(candidate_p0)
            paired_gains.append(
                _signed_normal_gain(normal_player, candidate_p0, challenger_p0)
            )

        profile_mean, profile_se = _mean_se(candidate_values)
        gain_mean, gain_se = _mean_se(paired_gains)
        metrics.append(
            PairedNormalFantasySeedMetric(
                seed_id=str(spec.seed_id),
                samples=config.heldout_samples_per_seed,
                profile_p0_value=profile_mean,
                profile_value_standard_error=profile_se,
                signed_normal_gain=gain_mean,
                gain_standard_error=gain_se,
                normal_player=normal_player,
            )
        )

    aggregate_mean, aggregate_se = _mean_se(
        [metric.signed_normal_gain for metric in metrics]
    )
    conservative = max(
        0.0,
        aggregate_mean - config.confidence_multiplier * aggregate_se,
    )
    aggregate = PairedNormalFantasyAggregate(
        normal_player=normal_player,
        seed_mean_signed_gain=aggregate_mean,
        seed_standard_error=aggregate_se,
        confidence_multiplier=config.confidence_multiplier,
        conservative_lower_signal=conservative,
    )

    payload: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "authority": AUTHORITY,
        "state": state.as_key(),
        "continuation_sha256": continuation_sha,
        "candidate_oracle_id": candidate.oracle_id,
        "candidate_snapshot_sha256": candidate.snapshot.sha256,
        "challenger_oracle_id": challenger.oracle_id,
        "challenger_snapshot_sha256": challenger.snapshot.sha256,
        "terminal_evaluator_id": terminal_id,
        "config_sha256": config.sha256,
        "normal_player": normal_player,
        "heldout_seed_ids": list(seed_ids),
        "heldout_samples_per_seed": config.heldout_samples_per_seed,
        "paired_seed_metrics": [metric.__dict__ for metric in metrics],
        "aggregate": aggregate.__dict__,
        "max_conservative_deviation_signal": conservative,
        "provenance": provenance_text,
        "certification_eligible": False,
    }
    return PairedNormalFantasyScreeningReport(
        state=state.as_key(),
        continuation_sha256=continuation_sha,
        candidate_oracle_id=candidate.oracle_id,
        candidate_snapshot_sha256=candidate.snapshot.sha256,
        challenger_oracle_id=challenger.oracle_id,
        challenger_snapshot_sha256=challenger.snapshot.sha256,
        terminal_evaluator_id=terminal_id,
        config_sha256=config.sha256,
        normal_player=normal_player,
        heldout_seed_ids=seed_ids,
        heldout_samples_per_seed=config.heldout_samples_per_seed,
        paired_seed_metrics=tuple(metrics),
        aggregate=aggregate,
        max_conservative_deviation_signal=conservative,
        provenance=provenance_text,
        sha256=_sha(payload),
    )
