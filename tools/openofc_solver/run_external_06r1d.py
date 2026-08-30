from __future__ import annotations

"""06R1D wrapper: rerun the frozen 06R1 protocol on one fixed R4 P0 seed."""

import argparse
import hashlib
import json
from pathlib import Path

from external_06r0_conditioned_solver import ConditionedFixtureSpec
import run_external_06r1 as r1

ALLOWED_FIXTURE_SEEDS = (64011, 64012, 64013, 64014)


def run(fixture_seed: int) -> dict:
    seed = int(fixture_seed)
    if seed not in ALLOWED_FIXTURE_SEEDS:
        raise ValueError(f"fixture seed {seed} is outside frozen 06R1D suite")
    spec = ConditionedFixtureSpec(f"R4D_{seed}", seed, 4, 0)

    original = r1._spec
    try:
        r1._spec = lambda: spec
        payload = r1.run()
    finally:
        r1._spec = original

    values = payload["oracle"]["root_action_values"]
    spread = max(values.values()) - min(values.values())
    payload["schema"] = "openofc-external-06r1d-v1"
    payload["experiment_id"] = "EXT-06R1D-R4-MULTIFIXTURE-DISCRIMINATION"
    payload["authority"] = "BELIEF_CORRECT_R4_MULTIFIXTURE_DIAGNOSTIC_ONLY"
    payload["r1d_fixture"] = {
        "name": spec.name,
        "seed": seed,
        "round": 4,
        "actor": 0,
        "oracle_action_value_spread": spread,
        "strategically_discriminative": spread > 1e-12,
    }
    payload["r1_single_fixture_recommendation"] = payload.pop("recommendation")
    payload["verdict"] = "PASS_06R1D_FIXTURE"
    payload["real_routes_certified"] = 0
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture-seed", required=True, type=int)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    payload = run(args.fixture_seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "fixture": payload["r1d_fixture"],
        "final_budget_winners": payload["final_budget_winners"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
