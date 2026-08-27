from __future__ import annotations

"""F17 companion to the M5N F14 phase-timed runtime calibration.

This calibration is runtime-only.  Phase start markers are flushed before each
expensive operation so a workflow timeout identifies the phase that failed to
finish rather than yielding an opaque no-artifact cancellation.
"""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from time import perf_counter

from hu_continuation import HUContinuationState, zero_continuation_values
from m5b_adaptive_normal_oracles import AdaptiveNormalFantasyOracle
from m5n_normal_fantasy_paired_screening import screen_paired_normal_fantasy_candidate
from normal_fantasy_terminal import ExactOnePassNormalFantasyTerminalEvaluator
from run_m5n_normal_fantasy_runtime_calibration import (
    CANDIDATE_CONFIG,
    CHALLENGER_CONFIG,
    HELDOUT_SEEDS,
    SCREEN_CONFIG,
)

SCHEMA = "openofc-m5n-normal-fantasy-runtime-calibration-f17-v2"
AUTHORITY = "RUNTIME_CALIBRATION_NOT_STRATEGIC_EVIDENCE"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5n_normal_fantasy_runtime_calibration_f17.json"
STATE = HUContinuationState(1, 17, 0)


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _phase(label: str, event: str, **extra: object) -> None:
    payload = {"phase": label, "event": event, **extra}
    print("M5N_F17_PHASE " + json.dumps(payload, sort_keys=True), flush=True)


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
    _phase("candidate_materialization", "start")
    phase_start = perf_counter()
    candidate = candidate_oracle.materialize_fixed_policy(STATE, values)
    candidate_seconds = perf_counter() - phase_start
    candidate_eval_count = terminal.evaluations
    _phase(
        "candidate_materialization",
        "done",
        seconds=candidate_seconds,
        terminal_evaluations=candidate_eval_count,
    )

    _phase("challenger_materialization", "start")
    phase_start = perf_counter()
    challenger = challenger_oracle.materialize_fixed_policy(STATE, values)
    challenger_seconds = perf_counter() - phase_start
    challenger_eval_count = terminal.evaluations - candidate_eval_count
    _phase(
        "challenger_materialization",
        "done",
        seconds=challenger_seconds,
        terminal_evaluations=challenger_eval_count,
    )

    _phase("paired_screening", "start")
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
        provenance="M5N F17 phase-timed runtime calibration after run 33089463461 timeout",
    )
    screening_seconds = perf_counter() - phase_start
    screening_eval_count = terminal.evaluations - candidate_eval_count - challenger_eval_count
    _phase(
        "paired_screening",
        "done",
        seconds=screening_seconds,
        terminal_evaluations=screening_eval_count,
    )
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
    phase_names = (
        "candidate_materialization",
        "challenger_materialization",
        "paired_screening",
    )
    phase_seconds = (candidate_seconds, challenger_seconds, screening_seconds)
    dominant_phase = phase_names[max(range(3), key=lambda index: phase_seconds[index])]

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "source_timeout_run": 33089463461,
        "source_f17_timeout_run": 33114482820,
        "companion_f14_payload_sha256": "2ecfe913abf6d7d0c7ef8697be55ec9733515731b470cd0b778345de8258847e",
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
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "timings": timings, "summary": payload["summary"]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
