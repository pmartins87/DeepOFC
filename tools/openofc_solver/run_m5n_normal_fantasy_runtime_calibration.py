from __future__ import annotations

"""Phase-timed M5N runtime calibration after the 180-minute pilot timeout.

This is intentionally much smaller than the strategic pilot.  It measures where
CPU time is spent; its screening numbers have no strategic/certification authority.
"""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from time import perf_counter

from hu_continuation import HUContinuationState, zero_continuation_values
from m5b_adaptive_normal_oracles import AdaptiveNormalConfig, AdaptiveNormalFantasyOracle
from m5k_normal_fantasy_screening import HeldoutSeedSpec
from m5n_normal_fantasy_paired_screening import (
    PairedNormalFantasyConfig,
    screen_paired_normal_fantasy_candidate,
)
from normal_fantasy_terminal import ExactOnePassNormalFantasyTerminalEvaluator

SCHEMA = "openofc-m5n-normal-fantasy-runtime-calibration-v1"
AUTHORITY = "RUNTIME_CALIBRATION_NOT_STRATEGIC_EVIDENCE"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5n_normal_fantasy_runtime_calibration.json"
STATE = HUContinuationState(0, 0, 14)

CANDIDATE_CONFIG = AdaptiveNormalConfig(
    training_iterations=8,
    evaluation_samples=8,
    replay_capacity=1_000,
    fit_epochs=1,
    model_buckets=1 << 8,
    learning_rate=0.08,
    l2=1e-6,
    huber_delta=1.0,
    epsilon=0.6,
    base_seed=2026083011,
)
CHALLENGER_CONFIG = AdaptiveNormalConfig(
    training_iterations=16,
    evaluation_samples=8,
    replay_capacity=2_000,
    fit_epochs=1,
    model_buckets=1 << 9,
    learning_rate=0.08,
    l2=1e-6,
    huber_delta=1.0,
    epsilon=0.6,
    base_seed=2026083037,
)
SCREEN_CONFIG = PairedNormalFantasyConfig(
    heldout_samples_per_seed=4,
    confidence_multiplier=3.182,
    base_seed=2026083061,
)
HELDOUT_SEEDS = (
    HeldoutSeedSpec("m5n-runtime-01:2026083073", 2026083073),
    HeldoutSeedSpec("m5n-runtime-02:2026083089", 2026083089),
    HeldoutSeedSpec("m5n-runtime-03:2026083107", 2026083107),
    HeldoutSeedSpec("m5n-runtime-04:2026083121", 2026083121),
)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def main() -> None:
    values = zero_continuation_values()
    terminal = ExactOnePassNormalFantasyTerminalEvaluator()

    candidate_oracle = AdaptiveNormalFantasyOracle(
        CANDIDATE_CONFIG,
        terminal_evaluator=terminal,
        terminal_evaluator_id=terminal.authority,
    )
    challenger_oracle = AdaptiveNormalFantasyOracle(
        CHALLENGER_CONFIG,
        terminal_evaluator=terminal,
        terminal_evaluator_id=terminal.authority,
    )

    wall_start = perf_counter()
    phase_start = perf_counter()
    candidate = candidate_oracle.materialize_fixed_policy(STATE, values)
    candidate_seconds = perf_counter() - phase_start
    candidate_eval_count = terminal.evaluations

    phase_start = perf_counter()
    challenger = challenger_oracle.materialize_fixed_policy(STATE, values)
    challenger_seconds = perf_counter() - phase_start
    challenger_eval_count = terminal.evaluations - candidate_eval_count

    phase_start = perf_counter()
    screen = screen_paired_normal_fantasy_candidate(
        candidate.fixed_oracle,
        challenger.fixed_oracle,
        STATE,
        values,
        HELDOUT_SEEDS,
        SCREEN_CONFIG,
        terminal_evaluator=terminal,
        terminal_evaluator_id=terminal.authority,
        provenance="M5N phase-timed runtime calibration after run 33089463461 timeout",
    )
    screening_seconds = perf_counter() - phase_start
    screening_eval_count = terminal.evaluations - candidate_eval_count - challenger_eval_count
    total_seconds = perf_counter() - wall_start

    timings = {
        "candidate_materialization_seconds": candidate_seconds,
        "challenger_materialization_seconds": challenger_seconds,
        "paired_screening_seconds": screening_seconds,
        "total_measured_seconds": total_seconds,
        "candidate_terminal_evaluations": candidate_eval_count,
        "challenger_terminal_evaluations": challenger_eval_count,
        "screening_terminal_evaluations": screening_eval_count,
        "terminal_evaluations_total": terminal.evaluations,
        "terminal_exact_cache_hits": terminal.exact_hits,
        "terminal_exact_cache_misses": terminal.exact_misses,
    }
    positive = [
        candidate_seconds,
        challenger_seconds,
        screening_seconds,
    ]
    dominant_index = max(range(3), key=lambda index: positive[index])
    dominant_phase = (
        "candidate_materialization",
        "challenger_materialization",
        "paired_screening",
    )[dominant_index]

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "source_timeout_run": 33089463461,
        "state": STATE.as_key(),
        "candidate_config": CANDIDATE_CONFIG.payload(),
        "challenger_config": CHALLENGER_CONFIG.payload(),
        "screen_config": SCREEN_CONFIG.payload(),
        "heldout_seeds": [asdict(seed) for seed in HELDOUT_SEEDS],
        "candidate_materialization": asdict(candidate.report),
        "challenger_materialization": asdict(challenger.report),
        "screening_report": asdict(screen),
        "timings": timings,
        "summary": {
            "dominant_phase": dominant_phase,
            "total_measured_seconds": total_seconds,
            "original_pilot_strategic_result_available": False,
            "calibration_is_strategic_evidence": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "timings": timings, "summary": payload["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
