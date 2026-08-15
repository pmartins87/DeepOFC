from __future__ import annotations

import time

from deepofc.hu_cfr import FullTreeCFR
from deepofc.hu_subgame import HUFinalRoundSubgame


def main() -> None:
    game = HUFinalRoundSubgame()

    started = time.perf_counter()
    checks = game.assert_terminal_swap_symmetry()
    symmetry_seconds = time.perf_counter() - started
    if checks != 40320:
        raise SystemExit(f"unexpected symmetry terminal count: {checks}")

    uniform = game.uniform_profile()
    uniform_value = game.expected_u0(uniform)
    uniform_br0 = game.best_response_value(uniform, 0)
    uniform_br1 = game.best_response_value(uniform, 1)
    uniform_exploitability = 0.5 * (uniform_br0 + uniform_br1)

    print(
        "subgame "
        f"chance_outcomes={len(game.outcomes)} "
        f"infosets={len(game.info_actions)} "
        f"merged_second_infosets={game.count_merged_second_infosets()} "
        f"terminal_symmetry_checks={checks} "
        f"symmetry_seconds={symmetry_seconds:.6f}"
    )
    print(
        "uniform "
        f"expected_u0={uniform_value:.12f} "
        f"br0={uniform_br0:.12f} "
        f"br1={uniform_br1:.12f} "
        f"exploitability={uniform_exploitability:.12f}"
    )
    if abs(uniform_value) > 1e-12:
        raise SystemExit("symmetric uniform profile should have exact-zero expected value")
    if uniform_exploitability <= 0.0:
        raise SystemExit("benchmark needs a strategically nontrivial uniform starting profile")

    checkpoints = (1, 2, 4, 8, 16, 32, 64, 128, 256)
    finals: dict[str, float] = {}
    for variant in ("cfr_plus", "dcfr"):
        solver = FullTreeCFR(game, variant=variant)
        previous = 0
        variant_started = time.perf_counter()
        for checkpoint in checkpoints:
            solver.run(checkpoint - previous)
            previous = checkpoint
            snap = solver.snapshot()
            print(
                f"variant={variant} iteration={checkpoint} "
                f"expected_u0={snap.expected_u0:.12f} "
                f"br0={snap.br0:.12f} br1={snap.br1:.12f} "
                f"nash_conv={snap.nash_conv:.12f} "
                f"exploitability={snap.exploitability:.12f}"
            )
        elapsed = time.perf_counter() - variant_started
        final = solver.snapshot().exploitability
        finals[variant] = final
        print(f"variant={variant} total_seconds={elapsed:.6f} final_exploitability={final:.12f}")

    for variant, final in finals.items():
        if not final < uniform_exploitability:
            raise SystemExit(
                f"{variant} did not improve exploitability: final={final} uniform={uniform_exploitability}"
            )

    print("HU IMPERFECT-INFO CFR ARCHITECTURE BENCHMARK: PASS")


if __name__ == "__main__":
    main()
