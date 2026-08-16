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
from deepofc.hu_two_round_resolve import Round4PublicDCFR, Round4PublicState, build_round4_public_subgames

EPSILON = 0.01
RESOLVE_ITERATIONS = 256
MAX_ROUNDS = 2


def tremble_profile(game, current):
    uniform = game.uniform_profile()
    return {
        info: {
            action: (1.0 - EPSILON) * current[info][action] + EPSILON * uniform[info][action]
            for action in actions
        }
        for info, actions in game.info_actions.items()
    }


def steering_states(game, current, response):
    player = response.player
    states: dict[Round4PublicState, float] = {}
    for outcome in game.outcomes:
        first, second = outcome.first_player, outcome.second_player
        first_info = game.round3_first_info(outcome)
        if first == player:
            first_options = ((response.choices[first_info], 1.0),)
        else:
            first_options = tuple((a, p) for a, p in game._distribution(current, first_info).items() if p > 0.0)
        for first_action, p_first in first_options:
            second_info = game.round3_second_info(outcome, first_action)
            if second == player:
                second_options = ((response.choices[second_info], 1.0),)
            else:
                second_options = tuple((a, p) for a, p in game._distribution(current, second_info).items() if p > 0.0)
            for second_action, p_second in second_options:
                reach = game.chance_probability * p_first * p_second
                if reach <= 0.0:
                    continue
                state = Round4PublicState(
                    first_player=first,
                    first_round3_public=action_public_key(first_action),
                    second_round3_public=action_public_key(second_action),
                )
                states[state] = states.get(state, 0.0) + reach
    return states


def snapshot(game, profile):
    conv, br0, br1 = exact_nash_conv(game, profile)
    return 0.5 * conv, br0, br1


def repair_round(game, current, br0, br1):
    s0, s1 = steering_states(game, current, br0), steering_states(game, current, br1)
    targets = set(s0) | set(s1)
    current_support = set(build_round4_public_subgames(game, current))
    belief_public = build_round4_public_subgames(game, tremble_profile(game, current))
    if targets - set(belief_public):
        raise AssertionError("trembled belief misses exact-BR steering state")

    combined_reach = {state: s0.get(state, 0.0) + s1.get(state, 0.0) for state in targets}
    candidate = {info: dict(dist) for info, dist in current.items()}
    improved = skipped_zero = rejected = 0
    weighted_before = weighted_after = 0.0
    started = time.perf_counter()

    for state in sorted(targets, key=lambda s: combined_reach[s], reverse=True):
        sub = belief_public[state]
        before = sub.exploitability(current)
        weight = combined_reach[state]
        weighted_before += weight * before
        if before <= 1e-12:
            skipped_zero += 1
            weighted_after += weight * before
            continue
        resolver = Round4PublicDCFR(sub)
        resolver.run(RESOLVE_ITERATIONS)
        solved = resolver.average_profile()
        after = sub.exploitability(solved)
        if after + 1e-12 < before:
            improved += 1
            weighted_after += weight * after
            for info, dist in solved.items():
                candidate[info] = dict(dist)
        else:
            rejected += 1
            weighted_after += weight * before

    return candidate, {
        "targets": len(targets),
        "on_tree": len(targets & current_support),
        "off_tree": len(targets - current_support),
        "improved": improved,
        "skipped_zero": skipped_zero,
        "rejected": rejected,
        "weighted_before": weighted_before,
        "weighted_after": weighted_after,
        "seconds": time.perf_counter() - started,
    }


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=20260815)
    solver.run(5_000)
    current = solver.current_profile()
    exploitability, br0, br1 = snapshot(game, current)
    print(f"round=0 exploitability={exploitability:.12f}")

    accepted = 0
    for round_index in range(1, MAX_ROUNDS + 1):
        candidate, diag = repair_round(game, current, br0, br1)
        new_exp, new_br0, new_br1 = snapshot(game, candidate)
        delta = new_exp - exploitability
        accept = delta < -1e-12
        print(
            f"round={round_index} targets={diag['targets']} on_tree={diag['on_tree']} off_tree={diag['off_tree']} "
            f"improved={diag['improved']} skipped_zero={diag['skipped_zero']} rejected={diag['rejected']} "
            f"weighted_before={diag['weighted_before']:.12f} weighted_after={diag['weighted_after']:.12f} "
            f"resolve_seconds={diag['seconds']:.6f} candidate_exploitability={new_exp:.12f} "
            f"delta={delta:+.12f} accepted={int(accept)}"
        )
        if not accept:
            break
        current, exploitability, br0, br1 = candidate, new_exp, new_br0, new_br1
        accepted += 1

    if accepted < 1:
        raise SystemExit("no globally improving targeted repair round was accepted")
    print(f"accepted_rounds={accepted} final_exploitability={exploitability:.12f}")
    print("HU TWO-ROUND ITERATIVE BR-GUIDED TREMBLED RE-SOLVE V2: PASS")


if __name__ == "__main__":
    main()
