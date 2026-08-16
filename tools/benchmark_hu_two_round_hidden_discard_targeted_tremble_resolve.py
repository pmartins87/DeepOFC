from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import action_public_key
from deepofc.hu_two_round_br import exact_best_response, exact_nash_conv
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from deepofc.hu_two_round_resolve import (
    Round4PublicDCFR,
    Round4PublicState,
    build_round4_public_subgames,
)


EPSILON = 0.01
RESOLVE_ITERATIONS = 256


def exact_exploitability(game, profile):
    expected = game.expected_u0(profile)
    conv, br0, br1 = exact_nash_conv(game, profile)
    return expected, br0.value, br1.value, 0.5 * conv


def tremble_profile(game, current, epsilon: float):
    uniform = game.uniform_profile()
    out = {}
    for info, actions in game.info_actions.items():
        out[info] = {
            action: (1.0 - epsilon) * current[info][action]
            + epsilon * uniform[info][action]
            for action in actions
        }
    return out


def br_steering_public_states(game, current, response):
    """Public round-4 states reached by one exact BR versus the current opponent."""

    player = response.player
    states: dict[Round4PublicState, float] = {}
    for outcome in game.outcomes:
        first = outcome.first_player
        second = outcome.second_player
        first_info = game.round3_first_info(outcome)
        if first == player:
            first_options = ((response.choices[first_info], 1.0),)
        else:
            dist = game._distribution(current, first_info)
            first_options = tuple((a, p) for a, p in dist.items() if p > 0.0)

        for first_action, p_first in first_options:
            second_info = game.round3_second_info(outcome, first_action)
            if second == player:
                second_options = ((response.choices[second_info], 1.0),)
            else:
                dist = game._distribution(current, second_info)
                second_options = tuple((a, p) for a, p in dist.items() if p > 0.0)

            for second_action, p_second in second_options:
                reach = game.chance_probability * p_first * p_second
                if reach <= 0.0:
                    continue
                state = Round4PublicState(
                    first_player=outcome.first_player,
                    first_round3_public=action_public_key(first_action),
                    second_round3_public=action_public_key(second_action),
                )
                states[state] = states.get(state, 0.0) + reach
    return states


def run(seed: int) -> tuple[float, float]:
    game = HUTwoRoundHiddenDiscardSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=seed)
    started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - started
    current = solver.current_profile()

    started = time.perf_counter()
    before = exact_exploitability(game, current)
    before_seconds = time.perf_counter() - started
    br0 = exact_best_response(game, current, 0)
    br1 = exact_best_response(game, current, 1)

    steering0 = br_steering_public_states(game, current, br0)
    steering1 = br_steering_public_states(game, current, br1)
    target_states = set(steering0) | set(steering1)

    current_public = build_round4_public_subgames(game, current)
    current_support = set(current_public)
    off_tree_targets = target_states - current_support
    on_tree_targets = target_states & current_support
    if not off_tree_targets:
        raise SystemExit(
            f"seed={seed}: exact best responses exposed no zero-blueprint-reach public state"
        )

    belief = tremble_profile(game, current, EPSILON)
    started = time.perf_counter()
    belief_public = build_round4_public_subgames(game, belief)
    build_seconds = time.perf_counter() - started
    missing = target_states - set(belief_public)
    if missing:
        raise SystemExit(
            f"seed={seed}: trembled belief still lacks {len(missing)} BR steering states"
        )

    stitched = {info: dict(dist) for info, dist in current.items()}
    owners = {}
    improved = 0
    rejected = 0
    target_infosets = 0
    local_weighted_before = 0.0
    local_weighted_after = 0.0

    combined_reach = {
        state: steering0.get(state, 0.0) + steering1.get(state, 0.0)
        for state in target_states
    }

    started = time.perf_counter()
    for state in sorted(target_states, key=lambda s: combined_reach[s], reverse=True):
        sub = belief_public[state]
        for info in sub.info_actions:
            previous = owners.setdefault(info, state)
            if previous != state:
                raise SystemExit("round4 infoset belongs to multiple targeted public states")

        local_before = sub.exploitability(current)
        resolver = Round4PublicDCFR(sub)
        resolver.run(RESOLVE_ITERATIONS)
        candidate = resolver.average_profile()
        local_after = sub.exploitability(candidate)
        weight = combined_reach[state]
        local_weighted_before += weight * local_before
        if local_after + 1e-12 < local_before:
            improved += 1
            target_infosets += len(candidate)
            local_weighted_after += weight * local_after
            for info, dist in candidate.items():
                stitched[info] = dict(dist)
        else:
            rejected += 1
            local_weighted_after += weight * local_before
    resolve_seconds = time.perf_counter() - started

    started = time.perf_counter()
    after = exact_exploitability(game, stitched)
    after_seconds = time.perf_counter() - started
    delta = after[3] - before[3]

    print(
        f"seed={seed} blueprint iterations=5000 train_seconds={train_seconds:.6f} "
        f"expected_u0={before[0]:.12f} br0={before[1]:.12f} br1={before[2]:.12f} "
        f"exploitability={before[3]:.12f} exact_eval_seconds={before_seconds:.6f}"
    )
    print(
        f"seed={seed} br_steering states_br0={len(steering0)} states_br1={len(steering1)} "
        f"union={len(target_states)} on_tree={len(on_tree_targets)} off_tree={len(off_tree_targets)}"
    )
    print(
        f"seed={seed} belief epsilon={EPSILON:.6f} belief_public_states={len(belief_public)} "
        f"build_seconds={build_seconds:.6f} improved_targets={improved} rejected_targets={rejected} "
        f"stitched_infosets={target_infosets} resolve_seconds={resolve_seconds:.6f}"
    )
    print(
        f"seed={seed} weighted_target_local_before={local_weighted_before:.12f} "
        f"weighted_target_local_after={local_weighted_after:.12f}"
    )
    print(
        f"seed={seed} stitched expected_u0={after[0]:.12f} br0={after[1]:.12f} br1={after[2]:.12f} "
        f"exploitability={after[3]:.12f} global_delta={delta:+.12f} "
        f"exact_eval_seconds={after_seconds:.6f}"
    )
    if delta >= -1e-12:
        raise SystemExit(
            f"seed={seed}: BR-targeted trembled re-solving did not improve exact global exploitability: "
            f"delta={delta}"
        )
    print(f"seed={seed} HU TWO-ROUND BR-TARGETED TREMBLED RE-SOLVE: PASS")
    return before[3], after[3]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260815)
    args = ap.parse_args()
    run(args.seed)


if __name__ == "__main__":
    main()
