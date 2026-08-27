from __future__ import annotations

"""Measure one exact Normal/Fantasy terminal evaluation without training.

This is runtime instrumentation only.  It isolates the M4H exact terminal
frontier cost from M5B training and M5N paired screening so F17 bottlenecks can
be diagnosed without another multi-hour pilot.
"""

import argparse
import hashlib
import json
from pathlib import Path
import random
from time import perf_counter

from hu_continuation import HUContinuationState, zero_continuation_values
from normal_fantasy_kernel import (
    NormalFantasyState,
    child_normal_state,
    legal_normal_actions,
    sample_normal_fantasy_plan,
)
from normal_fantasy_terminal import ExactOnePassNormalFantasyTerminalEvaluator

SCHEMA = "openofc-m5n-exact-terminal-cost-microprobe-v1"
AUTHORITY = "RUNTIME_MICROPROBE_NOT_STRATEGIC_EVIDENCE"
ROOT = Path(__file__).resolve().parents[2]
SEEDS = {14: 2026090314, 17: 2026090317}


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _meta(count: int) -> HUContinuationState:
    if count == 14:
        return HUContinuationState(0, 0, 14)
    if count == 17:
        return HUContinuationState(1, 17, 0)
    raise ValueError("microprobe supports only F14 and F17")


def _deterministic_terminal(count: int) -> NormalFantasyState:
    plan = sample_normal_fantasy_plan(random.Random(SEEDS[count]), count)
    state = NormalFantasyState(current_meta=_meta(count), plan=plan)
    while not state.terminal():
        actions = legal_normal_actions(state)
        if not actions:
            raise RuntimeError("microprobe reached a nonterminal state without legal actions")
        action = sorted(actions, key=lambda candidate: candidate.key())[0]
        state = child_normal_state(state, action)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fantasy-count", type=int, choices=(14, 17), required=True)
    args = parser.parse_args()
    count = int(args.fantasy_count)
    print(f"M5N_TERMINAL_MICROPROBE_START fantasy_count={count}", flush=True)

    build_start = perf_counter()
    state = _deterministic_terminal(count)
    terminal_state_seconds = perf_counter() - build_start
    print(
        f"M5N_TERMINAL_STATE_READY fantasy_count={count} seconds={terminal_state_seconds:.6f}",
        flush=True,
    )

    evaluator = ExactOnePassNormalFantasyTerminalEvaluator()
    eval_start = perf_counter()
    result = evaluator.evaluate(state, zero_continuation_values())
    exact_seconds = perf_counter() - eval_start
    print(
        f"M5N_TERMINAL_EXACT_DONE fantasy_count={count} seconds={exact_seconds:.6f} "
        f"cache_hits={evaluator.exact_hits} cache_misses={evaluator.exact_misses}",
        flush=True,
    )

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "fantasy_count": count,
        "seed": SEEDS[count],
        "state": _meta(count).as_key(),
        "normal_board": [
            [str(card) for card in row]
            for row in state.normal_board.rows()
        ],
        "terminal_state_construction_seconds": terminal_state_seconds,
        "exact_terminal_evaluation_seconds": exact_seconds,
        "utility_for_normal": result.utility_for_normal,
        "evaluator_authority": evaluator.authority,
        "terminal_evaluations": evaluator.evaluations,
        "cache_hits": evaluator.exact_hits,
        "cache_misses": evaluator.exact_misses,
        "strategic_evidence": False,
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    payload["sha256"] = _sha(payload)
    out = ROOT / "artifacts" / f"m5n_exact_terminal_cost_f{count}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(out.relative_to(ROOT)), "sha256": payload["sha256"], "exact_terminal_evaluation_seconds": exact_seconds}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
