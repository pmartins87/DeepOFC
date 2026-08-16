from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import action_public_key
from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from deepofc.hu_two_round_resolve import (
    Round4PublicDCFR,
    Round4PublicState,
    build_round4_public_subgames,
)


EPSILON = 0.01
RESOLVE_ITERATIONS = 256
MAX_ROUNDS = 4


def tremble_profile(game, current, epsilon: float):
    uniform = game.uniform_profile()
    return {
        info: {
            action: (1.0 - epsilon) * current[info][action]
            + epsilon * uniform[info][action]
            for action in actions
        }
        for info, actions in game.info_actions.items()
    }


def steering_states(game, current, response):
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


def exact_snapshot(game, profile):
    expected = game.expected_u0(profile)
    conv, br0, br1 = exact_nash_conv(game, profile)
    return expected, br0.value, br1.value, 0.5 * conv, br0, br1


def one_candidate_round(game, current, br0, br1):
    s0 = steering_states(game, current, br0)
    s1 = steering_states(game, current, br1)
    targets = set(s0) | set(s1)
    current_support = set(build_round4_public_subgames(game, current))
    belief_public = build_round4_public_subgames(
        game, tremble_profile(game, current, EPSILON)
    )
    missing = targets - set(belief_public)
    if missing:
        raise AssertionError(f"trembled belief misses {len(missing)} steering states")

    combined_reach = {state: s0.get(state, 0.0) + s1.get(state, 0.0) for state in targets}
    candidate = {info: dict(dist) for info, dist in current.items()}
    owners = {}
    improved = 0
    rejected = 0
    stitched_infosets = 0
    weighted_before = 0.0
    weighted_after = 0.0

    for state in sorted(targets, key=lambda s: combined_reach[s], reverse=True):
        sub = belief_public[state]
        for info in sub.info_actions:
            previous = owners.setdefault(info, state)
            if previous != state:
                raise AssertionError("one round4 infoset belongs to multiple public states")
        local_before = sub.exploitability(current)
        resolver = Round4PublicDCFR(sub)
        resolver.run(RESOLVE_ITERATIONS)
        solved = resolver.average_profile()
        local_after = sub.exploitability(solved)
        weight = combined_reach[state]
        weighted_before += weight * local_before
        if local_after + 1e-12 < local_before:
            improved += 1
            stitched_infosets += len(solved)
            weighted_after += weight * local_after
            for info, dist in solved.items():
                candidate[info] = dict(dist)
        else:
            rejected += 1
            weighted_after += weight * local_before

    diagnostics = {
        "states_br0": len(s0),
        "states_br1": len(s1),
        "targets": len(targets),
        "on_tree": len(targets & current_support),
        "off_tree": len(targets - current_support),
        "improved": improved,
        "rejected": rejected,
        "stitched_infosets": stitched_infosets,
        "weighted_before": weighted_before,
        "weighted_after": weighted_after,
    }
    return candidate, diagnostics


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=20260815)
    started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - started
    current = solver.current_profile()

    started = time.perf_counter()
    snapshot = exact_snapshot(game, current)
    exact_seconds = time.perf_counter() - started
    print(
        f"round=0 source=blueprint expected_u0={snapshot[0]:.12f} br0={snapshot[1]:.12f} "
        f"br1={snapshot[2]:.12f} exploitability={snapshot[3]:.12f} "
        f"train_seconds={train_seconds:.6f} exact_seconds={exact_seconds:.6f}"
    )

    accepted = 0
    for round_index in range(1, MAX_ROUNDS + 1):
        started = time.perf_counter()
        candidate, diag = one_candidate_round(game, current, snapshot[4], snapshot[5])
        resolve_seconds = time.perf_counter() - started

        started = time.perf_counter()
        candidate_snapshot = exact_snapshot(game, candidate)
        exact_seconds = time.perf_counter() - started
        delta = candidate_snapshot[3] - snapshot[3]
        accept = delta < -1e-12
        print(
            f"round={round_index} targets={diag['targets']} on_tree={diag['on_tree']} "
            f"off_tree={diag['off_tree']} improved_local={diag['improved']} "
            f"rejected_local={diag['rejected']} stitched_infosets={diag['stitched_infosets']} "
            f"weighted_local_before={diag['weighted_before']:.12f} "
            f"weighted_local_after={diag['weighted_after']:.12f} "
            f"resolve_seconds={resolve_seconds:.6f}"
        )
        print(
            f"round={round_index} candidate expected_u0={candidate_snapshot[0]:.12f} "
            f"br0={candidate_snapshot[1]:.12f} br1={candidate_snapshot[2]:.12f} "
            f"exploitability={candidate_snapshot[3]:.12f} delta={delta:+.12f} "
            f"accepted={int(accept)} exact_seconds={exact_seconds:.6f}"
        )
        if not accept:
            break
        current = candidate
        snapshot = candidate_snapshot
        accepted += 1
        if snapshot[3] <= 1e-10:
            break

    if accepted == 0:
        raise SystemExit("iterative targeted re-solving accepted no globally improving round")
    print(
        f"summary accepted_rounds={accepted} final_expected_u0={snapshot[0]:.12f} "
        f"final_br0={snapshot[1]:.12f} final_br1={snapshot[2]:.12f} "
        f"final_exploitability={snapshot[3]:.12f}"
    )
    print("HU TWO-ROUND ITERATIVE BR-GUIDED TREMBLED RE-SOLVE: PASS")


if __name__ == "__main__":
    main()
