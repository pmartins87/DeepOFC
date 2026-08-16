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


EPSILON = 0.01
ITERATIONS = 256


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


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=20260815)
    started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - started
    current = solver.current_profile()

    started = time.perf_counter()
    before = exact_exploitability(game, current)
    before_seconds = time.perf_counter() - started

    belief_profile = tremble_profile(game, current, EPSILON)
    subgames = build_round4_public_subgames(game, belief_profile)
    if len(subgames) <= 39:
        raise SystemExit(
            f"trembled belief failed to expand public support: {len(subgames)} states"
        )

    # An infoset at round 4 is tied to exactly one public state. Resolve every
    # compatible state under the trembled posterior, but keep the actual round-3
    # play policy unchanged. Exact full-game BR will decide whether these off-tree
    # continuation choices are globally safer against steering deviations.
    owners = {}
    stitched = {info: dict(dist) for info, dist in current.items()}
    improved_local = 0
    kept_current_local = 0
    resolved_infosets = 0
    started = time.perf_counter()
    for state, sub in subgames.items():
        for info in sub.info_actions:
            previous = owners.setdefault(info, state)
            if previous != state:
                raise SystemExit("round4 infoset belongs to multiple public states")

        current_local = sub.exploitability(current)
        resolver = Round4PublicDCFR(sub)
        resolver.run(ITERATIONS)
        candidate = resolver.average_profile()
        candidate_local = sub.exploitability(candidate)
        # Under the chosen trembled belief, never knowingly replace a locally
        # better current continuation with a worse resolved approximation.
        if candidate_local + 1e-12 < current_local:
            improved_local += 1
            resolved_infosets += len(candidate)
            for info, dist in candidate.items():
                stitched[info] = dict(dist)
        else:
            kept_current_local += 1
    resolve_seconds = time.perf_counter() - started

    started = time.perf_counter()
    after = exact_exploitability(game, stitched)
    after_seconds = time.perf_counter() - started
    delta = after[3] - before[3]

    print(
        f"blueprint iterations=5000 train_seconds={train_seconds:.6f} "
        f"expected_u0={before[0]:.12f} br0={before[1]:.12f} br1={before[2]:.12f} "
        f"exploitability={before[3]:.12f} exact_eval_seconds={before_seconds:.6f}"
    )
    print(
        f"tremble epsilon={EPSILON:.6f} public_states={len(subgames)} "
        f"improved_local={improved_local} kept_current_local={kept_current_local} "
        f"stitched_infosets={resolved_infosets} resolve_seconds={resolve_seconds:.6f}"
    )
    print(
        f"stitched expected_u0={after[0]:.12f} br0={after[1]:.12f} br1={after[2]:.12f} "
        f"exploitability={after[3]:.12f} global_delta={delta:+.12f} "
        f"exact_eval_seconds={after_seconds:.6f}"
    )
    if delta >= -1e-12:
        raise SystemExit(
            "trembled-belief off-tree re-solving did not improve exact global exploitability: "
            f"delta={delta}"
        )
    print("HU TWO-ROUND HIDDEN-DISCARD TREMBLED-BELIEF RE-SOLVE: PASS")


if __name__ == "__main__":
    main()
