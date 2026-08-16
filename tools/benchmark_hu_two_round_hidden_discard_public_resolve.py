from __future__ import annotations

from pathlib import Path
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round_br import exact_nash_conv
from deepofc.hu_two_round_hidden_discard import HUTwoRoundHiddenDiscardSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from deepofc.hu_two_round_resolve import Round4PublicDCFR, build_round4_public_subgames


def exact_exploitability(game, profile) -> tuple[float, float, float, float]:
    expected = game.expected_u0(profile)
    conv, br0, br1 = exact_nash_conv(game, profile)
    return expected, br0.value, br1.value, 0.5 * conv


def main() -> None:
    game = HUTwoRoundHiddenDiscardSubgame()
    solver = TwoRoundExternalSamplingMCCFR(game, seed=20260815)

    started = time.perf_counter()
    solver.run(5_000)
    train_seconds = time.perf_counter() - started
    blueprint = solver.current_profile()

    started = time.perf_counter()
    full_before = exact_exploitability(game, blueprint)
    full_before_seconds = time.perf_counter() - started

    subgames = build_round4_public_subgames(game, blueprint)
    mass = sum(sub.public_reach_probability for sub in subgames.values())
    decomposed = sum(
        sub.public_reach_probability * sub.expected_u0(blueprint)
        for sub in subgames.values()
    )
    if abs(mass - 1.0) > 1e-10 or abs(decomposed - full_before[0]) > 1e-10:
        raise SystemExit(
            "hidden-discard public decomposition mismatch: "
            f"mass={mass} decomposed={decomposed} full={full_before[0]}"
        )

    # Exact local exploitability is cheap once the terminal cache is warm, but
    # scan only the highest-reach public states to keep this gate representative
    # of a runtime decision rather than optimizing a vanishingly rare branch.
    candidates = sorted(
        subgames.values(),
        key=lambda sub: sub.public_reach_probability,
        reverse=True,
    )[:64]
    scored = []
    scan_started = time.perf_counter()
    for sub in candidates:
        local_exp = sub.exploitability(blueprint)
        scored.append((sub.public_reach_probability * local_exp, local_exp, sub))
    scan_seconds = time.perf_counter() - scan_started
    score, local_before, target = max(scored, key=lambda item: (item[0], item[1]))
    if local_before <= 1e-12:
        raise SystemExit("top-64 reachable public states contain no exploitable continuation")

    # Each round-4 infoset must belong to exactly one public state. This is what
    # permits a local solved profile to be stitched back into the full strategy
    # without silently overwriting an unrelated public branch.
    owners = {}
    for state, sub in subgames.items():
        for info in sub.info_actions:
            previous = owners.setdefault(info, state)
            if previous != state:
                raise SystemExit("round4 infoset belongs to multiple public states")

    resolver = Round4PublicDCFR(target)
    started = time.perf_counter()
    resolver.run(256)
    resolve_seconds = time.perf_counter() - started
    resolved = resolver.average_profile()
    local_after = target.exploitability(resolved)
    if not math.isfinite(local_after) or local_after >= local_before:
        raise SystemExit(
            "conditioned DCFR failed to improve selected local game: "
            f"before={local_before} after={local_after}"
        )

    stitched = {info: dict(dist) for info, dist in blueprint.items()}
    for info, dist in resolved.items():
        stitched[info] = dict(dist)

    started = time.perf_counter()
    full_after = exact_exploitability(game, stitched)
    full_after_seconds = time.perf_counter() - started
    global_delta = full_after[3] - full_before[3]
    safety = "IMPROVED" if global_delta < -1e-12 else (
        "UNCHANGED" if abs(global_delta) <= 1e-12 else "WORSENED"
    )

    print(
        f"blueprint iterations=5000 train_seconds={train_seconds:.6f} "
        f"expected_u0={full_before[0]:.12f} br0={full_before[1]:.12f} "
        f"br1={full_before[2]:.12f} exploitability={full_before[3]:.12f} "
        f"exact_eval_seconds={full_before_seconds:.6f}"
    )
    print(
        f"public_states={len(subgames)} top_reach_scanned={len(candidates)} "
        f"scan_seconds={scan_seconds:.6f} decomposition_error={abs(decomposed-full_before[0]):.18e}"
    )
    print(
        f"target reach={target.public_reach_probability:.12f} score={score:.12f} "
        f"hidden_histories={len(target.histories)} infosets={len(target.info_actions)} "
        f"local_before={local_before:.12f} local_after={local_after:.12f} "
        f"resolve_seconds={resolve_seconds:.6f}"
    )
    print(
        f"stitched expected_u0={full_after[0]:.12f} br0={full_after[1]:.12f} "
        f"br1={full_after[2]:.12f} exploitability={full_after[3]:.12f} "
        f"global_exploitability_delta={global_delta:+.12f} safety={safety} "
        f"exact_eval_seconds={full_after_seconds:.6f}"
    )
    print("HU TWO-ROUND HIDDEN-DISCARD PUBLIC RE-SOLVE SAFETY: PASS")


if __name__ == "__main__":
    main()
