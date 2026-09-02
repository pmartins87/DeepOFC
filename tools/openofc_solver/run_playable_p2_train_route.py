from __future__ import annotations

"""Train and freeze one button route for the first PLAYABLE candidate."""

import argparse
import json
from pathlib import Path

from hu_continuation import HUContinuationState, zero_continuation_values
from m5b_adaptive_normal_oracles import AdaptiveNormalConfig, AdaptiveNormalNormalOracle
from playable_p2_candidate import build_route_payload, write_route
from strategic_continuation_cfr import ContinuationObjective


FROZEN_CONFIG = AdaptiveNormalConfig(
    training_iterations=4096,
    evaluation_samples=512,
    replay_capacity=100_000,
    fit_epochs=4,
    model_buckets=1 << 16,
    learning_rate=0.08,
    l2=1e-6,
    huber_delta=1.0,
    epsilon=0.6,
    base_seed=2026090201,
)


def train_route(
    *,
    button: int,
    source_commit: str,
    output: Path,
    config: AdaptiveNormalConfig = FROZEN_CONFIG,
) -> dict[str, object]:
    if button not in (0, 1):
        raise ValueError("button must be 0 or 1")
    state = HUContinuationState(button, 0, 0)
    continuation = zero_continuation_values()
    objective = ContinuationObjective(
        state,
        continuation,
        both_foul_policy=config.both_foul_policy,
    )
    materialized = AdaptiveNormalNormalOracle(config).materialize_fixed_policy(
        state, continuation
    )
    payload = build_route_payload(
        materialized,
        state=state,
        config=config,
        objective=objective,
        source_commit=source_commit,
    )
    write_route(output, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--button", type=int, choices=(0, 1), required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = train_route(
        button=args.button,
        source_commit=args.source_commit,
        output=args.output,
    )
    print(
        json.dumps(
            {
                "state": payload["state"],
                "route_sha256": payload["sha256"],
                "model_sha256": payload["model_sha256"],
                "policy_snapshot_sha256": payload["policy_snapshot"]["sha256"],
                "authority": payload["authority"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
