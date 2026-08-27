from __future__ import annotations

"""Measure whether M5I tabular response training reaches held-out response infosets.

M5J showed exactly identical held-out metrics at 256 and 1024 response episodes.
This diagnostic measures the structural reason directly: at every held-out
responding-player decision it records whether the canonical visible infoset was
present in the tabular response learner.  Missing keys use M5I's documented
uniform fallback.

Diagnostic only; no strategic certification authority.
"""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random

from hu_continuation import HUContinuationState, identity_for_role, zero_continuation_values
from m5a_normal_normal_oracle import policy_for_visible_node
from m5b_adaptive_normal_oracles import AdaptiveNormalNormalOracle
from m5i_normal_normal_screening import LearnedResponsePolicy, _normalize, _sample_index, _seed64
from run_m5j_normal_normal_budget_ladder import (
    CANDIDATE_BASE_SEED,
    HELDOUT_SEEDS,
    RESPONSE_BASE_SEED,
    _candidate_config,
)
from strategic_cfr import HUState, child_state, sample_deal_plan
from strategic_suit_symmetry import canonical_node_view

SCHEMA = "openofc-m5j-response-overlap-diagnostic-v1"
AUTHORITY = "RESPONSE_OVERLAP_DIAGNOSTIC_NOT_CERTIFICATION"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "m5j_response_overlap_diagnostic.json"
RESPONSE_BUDGETS = (256, 1024)
HELDOUT_SAMPLES_PER_SEED = 128


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _measure_one(
    candidate,
    response: LearnedResponsePolicy,
    state: HUContinuationState,
    *,
    player: int,
) -> dict[str, object]:
    decision_visits = 0
    trained_hit_visits = 0
    heldout_keys: set[str] = set()
    hit_keys: set[str] = set()
    missing_keys: set[str] = set()

    for spec in sorted(HELDOUT_SEEDS, key=lambda row: str(row.seed_id)):
        chance_rng = random.Random(int(spec.seed))
        for sample_index in range(HELDOUT_SAMPLES_PER_SEED):
            plan = sample_deal_plan(chance_rng)
            rng = random.Random(_seed64(spec.seed, sample_index, f"p{player}-response"))
            node = HUState(plan=plan)
            while not node.terminal():
                key, pairs, _suit_map = canonical_node_view(node)
                action_keys = tuple(action_key for action_key, _action in pairs)
                persistent_actor = identity_for_role(state, node.actor)
                if persistent_actor == player:
                    decision_visits += 1
                    heldout_keys.add(key)
                    if key in response.nodes:
                        trained_hit_visits += 1
                        hit_keys.add(key)
                    else:
                        missing_keys.add(key)
                    probabilities = response.average_policy_for_visible_node(key, action_keys)
                else:
                    probabilities = _normalize(policy_for_visible_node(candidate.model, key, action_keys))
                selected = _sample_index(probabilities, rng)
                node = child_state(node, pairs[selected][1])

    unique_total = len(heldout_keys)
    unique_hits = len(hit_keys)
    return {
        "persistent_player": player,
        "training_infosets": len(response.nodes),
        "training_total_visits": sum(node.visits for node in response.nodes.values()),
        "heldout_response_decision_visits": decision_visits,
        "heldout_trained_hit_visits": trained_hit_visits,
        "heldout_fallback_visits": decision_visits - trained_hit_visits,
        "heldout_visit_hit_rate": (
            trained_hit_visits / decision_visits if decision_visits else 0.0
        ),
        "heldout_unique_response_infosets": unique_total,
        "heldout_unique_trained_hits": unique_hits,
        "heldout_unique_fallback_infosets": unique_total - unique_hits,
        "heldout_unique_hit_rate": unique_hits / unique_total if unique_total else 0.0,
        "sample_missing_key_sha256": _sha(sorted(missing_keys)[:128]),
    }


def main() -> None:
    continuation_values = zero_continuation_values()
    rows: list[dict[str, object]] = []
    for button in (0, 1):
        state = HUContinuationState(button, 0, 0)
        candidate_config = _candidate_config(256)
        if candidate_config.base_seed != CANDIDATE_BASE_SEED:
            raise AssertionError("M5J candidate seed drift")
        candidate = AdaptiveNormalNormalOracle(candidate_config).materialize_fixed_policy(
            state, continuation_values
        )

        learners: dict[int, LearnedResponsePolicy] = {}
        for player in (0, 1):
            seed = _seed64(RESPONSE_BASE_SEED, state.as_key(), "response-train", player)
            learners[player] = LearnedResponsePolicy(
                candidate.fixed_oracle,
                state,
                continuation_values,
                deviator_player=player,
                epsilon=0.6,
                seed=seed,
            )

        previous = 0
        for budget in RESPONSE_BUDGETS:
            increment = budget - previous
            if increment <= 0:
                raise AssertionError("response budgets must be strictly increasing")
            for learner in learners.values():
                learner.run(increment)
            for player in (0, 1):
                measured = _measure_one(
                    candidate.fixed_oracle,
                    learners[player],
                    state,
                    player=player,
                )
                rows.append(
                    {
                        "state": state.as_key(),
                        "response_budget": budget,
                        "candidate_snapshot_sha256": candidate.report.policy_snapshot_sha256,
                        **measured,
                    }
                )
            previous = budget

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "candidate_budget": 256,
        "response_budgets": list(RESPONSE_BUDGETS),
        "heldout_samples_per_seed": HELDOUT_SAMPLES_PER_SEED,
        "heldout_seeds": [asdict(seed) for seed in HELDOUT_SEEDS],
        "rows": rows,
        "summary": {
            "rows": len(rows),
            "max_visit_hit_rate": max(float(row["heldout_visit_hit_rate"]) for row in rows),
            "max_unique_hit_rate": max(float(row["heldout_unique_hit_rate"]) for row in rows),
            "min_visit_hit_rate": min(float(row["heldout_visit_hit_rate"]) for row in rows),
            "min_unique_hit_rate": min(float(row["heldout_unique_hit_rate"]) for row in rows),
            "certification_eligible": False,
        },
    }
    payload["sha256"] = _sha(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(OUT.relative_to(ROOT)), "sha256": payload["sha256"], "summary": payload["summary"], "rows": rows}, sort_keys=True))


if __name__ == "__main__":
    main()
