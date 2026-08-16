from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from deepofc.hu_two_round_resolve import Round4PublicDCFR, build_round4_public_subgames


def exact_exploitability(game, profile):
    expected = game.expected_u0(profile)
    conv, br0, br1 = exact_nash_conv(game, profile)
    return expected, br0.value, br1.value, 0.5 * conv


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=20260815)
    started = time.perf_counter()
    solver.run(5_000)
    blueprint_train_seconds = time.perf_counter() - started
    blueprint = solver.current_profile()

    started = time.perf_counter()
    before = exact_exploitability(game, blueprint)
    before_eval_seconds = time.perf_counter() - started
    subgames = build_round4_public_subgames(game, blueprint)

    stitched = {info: dict(dist) for info, dist in blueprint.items()}
    improved = 0
    already_solved = 0
    rejected = 0
    local_before_weighted = 0.0
    local_after_weighted = 0.0
    resolved_infosets = 0
    started = time.perf_counter()
    for sub in sorted(subgames.values(), key=lambda item: item.public_reach_probability, reverse=True):
        local_before = sub.exploitability(blueprint)
        local_before_weighted += sub.public_reach_probability * local_before
        if local_before <= 1e-12:
            already_solved += 1
            local_after_weighted += sub.public_reach_probability * local_before
            continue
        resolver = Round4PublicDCFR(sub)
        resolver.run(256)
        candidate = resolver.average_profile()
        local_after = sub.exploitability(candidate)
        if local_after + 1e-12 < local_before:
            improved += 1
            resolved_infosets += len(candidate)
            local_after_weighted += sub.public_reach_probability * local_after
            for info, dist in candidate.items():
                stitched[info] = dict(dist)
        else:
            rejected += 1
            local_after_weighted += sub.public_reach_probability * local_before
    resolve_seconds = time.perf_counter() - started

    started = time.perf_counter()
    after = exact_exploitability(game, stitched)
    after_eval_seconds = time.perf_counter() - started
    delta = after[3] - before[3]
    if delta >= -1e-12:
        raise SystemExit(
            "full reachable public re-solving did not improve exact global exploitability: "
            f"before={before[3]} after={after[3]} delta={delta}"
        )

    print(
        f"blueprint iterations=5000 train_seconds={blueprint_train_seconds:.6f} "
        f"expected_u0={before[0]:.12f} br0={before[1]:.12f} br1={before[2]:.12f} "
        f"exploitability={before[3]:.12f} exact_eval_seconds={before_eval_seconds:.6f}"
    )
    print(
        f"public_states={len(subgames)} improved={improved} already_solved={already_solved} "
        f"rejected={rejected} stitched_infosets={resolved_infosets} "
        f"weighted_local_before={local_before_weighted:.12f} "
        f"weighted_local_after={local_after_weighted:.12f} "
        f"resolve_seconds={resolve_seconds:.6f}"
    )
    print(
        f"stitched expected_u0={after[0]:.12f} br0={after[1]:.12f} br1={after[2]:.12f} "
        f"exploitability={after[3]:.12f} global_delta={delta:+.12f} "
        f"exact_eval_seconds={after_eval_seconds:.6f}"
    )
    print("HU TWO-ROUND HIDDEN-DISCARD FULL PUBLIC RE-SOLVE: PASS")


if __name__ == "__main__":
    main()
