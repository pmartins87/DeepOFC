from __future__ import annotations

"""M5M generalized unilateral-response screening for Normal/Normal routes.

M5M is deliberately non-certifying.  It addresses two limitations exposed by
M5J: exact-key fallback in held-out response play and lack of uncertainty on the
response-minus-candidate difference.
"""

from dataclasses import dataclass
import hashlib
import json
import math
import random
from types import SimpleNamespace
from typing import Mapping, Sequence

from fantasy_fantasy_payoff import continuation_fingerprint
from hu_continuation import (
    HUContinuationState,
    KERNEL_NORMAL_NORMAL,
    hand_kernel_kind,
    identity_for_role,
)
from m5a_normal_normal_oracle import (
    NormalNormalFixedPolicyOracle,
    model_fingerprint,
    policy_for_visible_node,
)
from m5h_normal_heldout_evidence import HeldoutNormalSeedMetric
from m5i_normal_normal_screening import (
    HeldoutSeedSpec,
    LearnedResponsePolicy,
    _normalize,
    _sample_index,
    _seed64,
    _terminal_p0_value,
)
from strategic_advantage_model import DeterministicReservoir, SparseActionAdvantageModel
from strategic_cfr import HUState, child_state, sample_deal_plan
from strategic_policy_distillation import distill_solver_nodes, evaluate_model_on_solver
from strategic_suit_symmetry import canonical_node_view

CONFIG_SCHEMA = "openofc-m5m-generalized-response-config-v1"
RESPONSE_SCHEMA = "openofc-m5m-generalized-response-materialization-v1"
REPORT_SCHEMA = "openofc-m5m-generalized-response-screening-v1"
AUTHORITY = "GENERALIZED_PAIRED_RESPONSE_SCREENING_ONLY"
MASK64 = (1 << 64) - 1


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _mean_se(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        raise ValueError("M5M mean/SE requires observations")
    mean = float(sum(values) / len(values))
    if len(values) == 1:
        return mean, 0.0
    variance = sum((float(x) - mean) ** 2 for x in values) / (len(values) - 1)
    return mean, float(math.sqrt(max(0.0, variance) / len(values)))


@dataclass(frozen=True)
class GeneralizedResponseConfig:
    response_training_iterations: int = 1024
    epsilon: float = 0.6
    replay_capacity: int = 80_000
    fit_epochs: int = 2
    model_buckets: int = 1 << 13
    learning_rate: float = 0.08
    l2: float = 1e-6
    huber_delta: float = 1.0
    heldout_samples_per_seed: int = 256
    confidence_multiplier: float = 3.182
    base_seed: int = 2026082941

    def __post_init__(self) -> None:
        positive_ints = (
            self.response_training_iterations,
            self.replay_capacity,
            self.fit_epochs,
            self.model_buckets,
            self.heldout_samples_per_seed,
        )
        if min(positive_ints) <= 0:
            raise ValueError("M5M integer budgets must be positive")
        if self.model_buckets & (self.model_buckets - 1):
            raise ValueError("M5M model_buckets must be a power of two")
        if not 0.0 < self.epsilon <= 1.0:
            raise ValueError("M5M epsilon must be in (0,1]")
        if self.learning_rate <= 0.0 or self.l2 < 0.0 or self.huber_delta <= 0.0:
            raise ValueError("M5M model hyperparameters are invalid")
        if not math.isfinite(self.confidence_multiplier) or self.confidence_multiplier <= 0.0:
            raise ValueError("M5M confidence multiplier must be positive and finite")

    def payload(self) -> dict[str, object]:
        return {
            "schema": CONFIG_SCHEMA,
            "response_training_iterations": self.response_training_iterations,
            "epsilon": self.epsilon,
            "replay_capacity": self.replay_capacity,
            "fit_epochs": self.fit_epochs,
            "model_buckets": self.model_buckets,
            "learning_rate": self.learning_rate,
            "l2": self.l2,
            "huber_delta": self.huber_delta,
            "heldout_samples_per_seed": self.heldout_samples_per_seed,
            "confidence_multiplier": self.confidence_multiplier,
            "base_seed": int(self.base_seed) & MASK64,
        }

    @property
    def sha256(self) -> str:
        return _sha(self.payload())


@dataclass(frozen=True)
class GeneralizedResponseMaterializationReport:
    state: str
    persistent_player: int
    training_seed_id: str
    training_iterations: int
    tabular_infosets: int
    tabular_total_visits: int
    replay_seed_id: str
    replay_size: int
    replay_seen: int
    distilled_nodes: int
    action_examples: int
    model_seed_id: str
    model_sha256: str
    fit_mean_huber_loss: float
    fit_updates: int
    validation_nodes: int
    validation_actions: int
    validation_mean_policy_l1: float
    validation_mean_policy_rmse: float
    validation_top1_accuracy: float
    validation_mean_target_entropy: float
    config_sha256: str
    sha256: str
    schema: str = RESPONSE_SCHEMA
    authority: str = AUTHORITY


@dataclass(frozen=True)
class GeneralizedResponsePolicy:
    persistent_player: int
    model: SparseActionAdvantageModel
    report: GeneralizedResponseMaterializationReport

    def policy_for_visible_node(
        self, key: str, action_keys: Sequence[str]
    ) -> tuple[float, ...]:
        if model_fingerprint(self.model) != self.report.model_sha256:
            raise ValueError("M5M generalized response model/report identity mismatch")
        return policy_for_visible_node(self.model, key, action_keys)


@dataclass(frozen=True)
class PairedSeedMetric:
    seed_id: str
    samples: int
    profile_p0_value: float
    profile_value_standard_error: float
    p0_signed_gain: float
    p0_gain_standard_error: float
    p1_signed_gain: float
    p1_gain_standard_error: float

    def as_m5h_diagnostic(self) -> HeldoutNormalSeedMetric:
        return HeldoutNormalSeedMetric(
            seed_id=self.seed_id,
            samples=self.samples,
            profile_p0_value=self.profile_p0_value,
            p0_deviation_gain=max(0.0, self.p0_signed_gain),
            p1_deviation_gain=max(0.0, self.p1_signed_gain),
        )


@dataclass(frozen=True)
class AggregateGainDiagnostic:
    persistent_player: int
    seed_mean_signed_gain: float
    seed_standard_error: float
    confidence_multiplier: float
    conservative_lower_signal: float


@dataclass(frozen=True)
class GeneralizedResponseScreeningReport:
    state: str
    continuation_sha256: str
    candidate_oracle_id: str
    candidate_model_sha256: str
    candidate_snapshot_sha256: str
    config_sha256: str
    response_materializations: tuple[GeneralizedResponseMaterializationReport, ...]
    heldout_seed_ids: tuple[str, ...]
    heldout_samples_per_seed: int
    paired_seed_metrics: tuple[PairedSeedMetric, ...]
    p0_aggregate: AggregateGainDiagnostic
    p1_aggregate: AggregateGainDiagnostic
    max_conservative_deviation_signal: float
    provenance: str
    sha256: str
    schema: str = REPORT_SCHEMA
    authority: str = AUTHORITY
    certification_eligible: bool = False


def _materialize_response(
    candidate: NormalNormalFixedPolicyOracle,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    *,
    persistent_player: int,
    config: GeneralizedResponseConfig,
) -> GeneralizedResponsePolicy:
    train_seed = _seed64(
        config.base_seed, state.as_key(), "m5m-response-train", persistent_player
    )
    learner = LearnedResponsePolicy(
        candidate,
        state,
        continuation_values,
        deviator_player=persistent_player,
        epsilon=config.epsilon,
        seed=train_seed,
    )
    train_report = learner.run(config.response_training_iterations)

    replay_seed = _seed64(
        config.base_seed, state.as_key(), "m5m-response-replay", persistent_player
    )
    replay = DeterministicReservoir(capacity=config.replay_capacity, seed=replay_seed)
    solver_view = SimpleNamespace(nodes=learner.nodes)
    distilled = distill_solver_nodes(solver_view, replay, include_holdout=False)
    if not replay.items:
        raise RuntimeError("M5M response distillation produced empty replay")

    model_seed = _seed64(
        config.base_seed, state.as_key(), "m5m-response-model", persistent_player
    )
    model = SparseActionAdvantageModel(
        buckets=config.model_buckets,
        learning_rate=config.learning_rate,
        l2=config.l2,
        huber_delta=config.huber_delta,
        seed=model_seed,
    )
    fit = model.fit(replay, epochs=config.fit_epochs)
    validation = evaluate_model_on_solver(model, solver_view, holdout_only=True)
    model_sha = model_fingerprint(model)

    payload: dict[str, object] = {
        "schema": RESPONSE_SCHEMA,
        "authority": AUTHORITY,
        "state": state.as_key(),
        "persistent_player": persistent_player,
        "training_seed_id": train_report.training_seed_id,
        "training_iterations": train_report.iterations,
        "tabular_infosets": train_report.infosets,
        "tabular_total_visits": train_report.total_visits,
        "replay_seed_id": f"m5m-response-replay:{replay_seed}",
        "replay_size": len(replay.items),
        "replay_seen": replay.seen,
        "distilled_nodes": int(distilled["nodes"]),
        "action_examples": int(distilled["action_examples"]),
        "model_seed_id": f"m5m-response-model:{model_seed}",
        "model_sha256": model_sha,
        "fit_mean_huber_loss": float(fit["mean_huber_loss"]),
        "fit_updates": int(fit["updates"]),
        "validation": validation.payload(),
        "config_sha256": config.sha256,
    }
    report = GeneralizedResponseMaterializationReport(
        state=state.as_key(),
        persistent_player=persistent_player,
        training_seed_id=train_report.training_seed_id,
        training_iterations=train_report.iterations,
        tabular_infosets=train_report.infosets,
        tabular_total_visits=train_report.total_visits,
        replay_seed_id=f"m5m-response-replay:{replay_seed}",
        replay_size=len(replay.items),
        replay_seen=replay.seen,
        distilled_nodes=int(distilled["nodes"]),
        action_examples=int(distilled["action_examples"]),
        model_seed_id=f"m5m-response-model:{model_seed}",
        model_sha256=model_sha,
        fit_mean_huber_loss=float(fit["mean_huber_loss"]),
        fit_updates=int(fit["updates"]),
        validation_nodes=validation.nodes,
        validation_actions=validation.actions,
        validation_mean_policy_l1=validation.mean_policy_l1,
        validation_mean_policy_rmse=validation.mean_policy_rmse,
        validation_top1_accuracy=validation.top1_accuracy,
        validation_mean_target_entropy=validation.mean_target_entropy,
        config_sha256=config.sha256,
        sha256=_sha(payload),
    )
    return GeneralizedResponsePolicy(
        persistent_player=persistent_player,
        model=model,
        report=report,
    )


def _rollout(
    candidate: NormalNormalFixedPolicyOracle,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    plan,
    *,
    policy_seed: int,
    response: GeneralizedResponsePolicy | None = None,
) -> float:
    rng = random.Random(int(policy_seed) & MASK64)
    node = HUState(plan=plan)
    while not node.terminal():
        key, pairs, _suit_map = canonical_node_view(node)
        action_keys = tuple(action_key for action_key, _action in pairs)
        persistent_actor = identity_for_role(state, node.actor)
        if response is not None and persistent_actor == response.persistent_player:
            probabilities = response.policy_for_visible_node(key, action_keys)
        else:
            probabilities = _normalize(
                policy_for_visible_node(candidate.model, key, action_keys)
            )
        selected = _sample_index(probabilities, rng)
        node = child_state(node, pairs[selected][1])
    return _terminal_p0_value(
        state,
        node,
        continuation_values,
        both_foul_policy=candidate.snapshot.both_foul_policy,
    )


def _aggregate_gain(
    persistent_player: int,
    seed_means: Sequence[float],
    confidence_multiplier: float,
) -> AggregateGainDiagnostic:
    mean, se = _mean_se(seed_means)
    lower = max(0.0, mean - confidence_multiplier * se)
    return AggregateGainDiagnostic(
        persistent_player=persistent_player,
        seed_mean_signed_gain=mean,
        seed_standard_error=se,
        confidence_multiplier=confidence_multiplier,
        conservative_lower_signal=lower,
    )


def screen_generalized_normal_normal_candidate(
    candidate: NormalNormalFixedPolicyOracle,
    state: HUContinuationState,
    continuation_values: Mapping[HUContinuationState, float],
    heldout_seeds: Sequence[HeldoutSeedSpec],
    config: GeneralizedResponseConfig = GeneralizedResponseConfig(),
    *,
    provenance: str,
) -> GeneralizedResponseScreeningReport:
    if hand_kernel_kind(state) != KERNEL_NORMAL_NORMAL:
        raise ValueError("M5M only supports Normal/Normal states")
    if not isinstance(candidate, NormalNormalFixedPolicyOracle):
        raise TypeError("M5M candidate must be a frozen NormalNormalFixedPolicyOracle")
    if model_fingerprint(candidate.model) != candidate.snapshot.model_sha256:
        raise ValueError("M5M candidate model/snapshot identity mismatch")
    seed_specs = tuple(heldout_seeds)
    if len(seed_specs) < 4:
        raise ValueError("M5M requires at least four held-out seed identities")
    seed_ids = tuple(str(row.seed_id) for row in seed_specs)
    if len(set(seed_ids)) != len(seed_ids):
        raise ValueError("M5M held-out seed ids must be unique")
    provenance_text = str(provenance).strip()
    if not provenance_text:
        raise ValueError("M5M provenance must be non-empty")

    checked, continuation_sha = continuation_fingerprint(continuation_values)
    if candidate.snapshot.training_continuation_sha256 != continuation_sha:
        raise ValueError("M5M candidate snapshot is stale for screened continuation vector")

    responses = {
        player: _materialize_response(
            candidate,
            state,
            checked,
            persistent_player=player,
            config=config,
        )
        for player in (0, 1)
    }

    metrics: list[PairedSeedMetric] = []
    for spec in sorted(seed_specs, key=lambda row: str(row.seed_id)):
        chance_rng = random.Random(int(spec.seed) & MASK64)
        baseline_values: list[float] = []
        p0_differences: list[float] = []
        p1_differences: list[float] = []
        for sample_index in range(config.heldout_samples_per_seed):
            plan = sample_deal_plan(chance_rng)
            paired_seed = _seed64(spec.seed, sample_index, "m5m-paired-policy")
            baseline = _rollout(
                candidate, state, checked, plan, policy_seed=paired_seed
            )
            p0_response = _rollout(
                candidate,
                state,
                checked,
                plan,
                policy_seed=paired_seed,
                response=responses[0],
            )
            p1_response = _rollout(
                candidate,
                state,
                checked,
                plan,
                policy_seed=paired_seed,
                response=responses[1],
            )
            baseline_values.append(baseline)
            p0_differences.append(p0_response - baseline)
            p1_differences.append(baseline - p1_response)

        profile_mean, profile_se = _mean_se(baseline_values)
        p0_mean, p0_se = _mean_se(p0_differences)
        p1_mean, p1_se = _mean_se(p1_differences)
        metrics.append(
            PairedSeedMetric(
                seed_id=str(spec.seed_id),
                samples=config.heldout_samples_per_seed,
                profile_p0_value=profile_mean,
                profile_value_standard_error=profile_se,
                p0_signed_gain=p0_mean,
                p0_gain_standard_error=p0_se,
                p1_signed_gain=p1_mean,
                p1_gain_standard_error=p1_se,
            )
        )

    p0_aggregate = _aggregate_gain(
        0, [row.p0_signed_gain for row in metrics], config.confidence_multiplier
    )
    p1_aggregate = _aggregate_gain(
        1, [row.p1_signed_gain for row in metrics], config.confidence_multiplier
    )
    max_signal = max(
        p0_aggregate.conservative_lower_signal,
        p1_aggregate.conservative_lower_signal,
    )

    response_reports = tuple(responses[player].report for player in (0, 1))
    payload: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "authority": AUTHORITY,
        "state": state.as_key(),
        "continuation_sha256": continuation_sha,
        "candidate_oracle_id": candidate.oracle_id,
        "candidate_model_sha256": candidate.snapshot.model_sha256,
        "candidate_snapshot_sha256": candidate.snapshot.sha256,
        "config_sha256": config.sha256,
        "response_materializations": [report.__dict__ for report in response_reports],
        "heldout_seed_ids": list(seed_ids),
        "heldout_samples_per_seed": config.heldout_samples_per_seed,
        "paired_seed_metrics": [row.__dict__ for row in metrics],
        "p0_aggregate": p0_aggregate.__dict__,
        "p1_aggregate": p1_aggregate.__dict__,
        "max_conservative_deviation_signal": max_signal,
        "provenance": provenance_text,
        "certification_eligible": False,
    }
    return GeneralizedResponseScreeningReport(
        state=state.as_key(),
        continuation_sha256=continuation_sha,
        candidate_oracle_id=candidate.oracle_id,
        candidate_model_sha256=candidate.snapshot.model_sha256,
        candidate_snapshot_sha256=candidate.snapshot.sha256,
        config_sha256=config.sha256,
        response_materializations=response_reports,
        heldout_seed_ids=seed_ids,
        heldout_samples_per_seed=config.heldout_samples_per_seed,
        paired_seed_metrics=tuple(metrics),
        p0_aggregate=p0_aggregate,
        p1_aggregate=p1_aggregate,
        max_conservative_deviation_signal=max_signal,
        provenance=provenance_text,
        sha256=_sha(payload),
    )
