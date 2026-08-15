from __future__ import annotations

from math import ceil, sqrt
from pathlib import Path
from statistics import mean
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deepofc.expectimax import evaluate_penultimate_normal_round_exact_last_chance
from deepofc.monte_carlo import evaluate_penultimate_normal_round_monte_carlo
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def fixture():
    hero = PlayerBoard(
        top=(C("6s"), C("6h")),
        middle=(C("7s"), C("7h"), C("5s")),
        bottom=(C("9s"), C("Ts"), C("Js"), C("Qs")),
    )
    opponent = PlayerBoard(
        top=(C("5c"), C("5d"), C("2c")),
        middle=(C("8c"), C("8d"), C("7c"), C("6c"), C("4c")),
        bottom=(C("Ac"), C("Kc"), C("Qc"), C("Jc"), C("Tc")),
    )
    state = OFCState(
        players=(PlayerState(chair=0, board=opponent), PlayerState(chair=1, board=hero)),
        hero_chair=1,
        dealer_chair=0,
        acting_chair=1,
        round_index=3,
        hero_incoming=(C("Ah"), C("8s"), C("4s")),
        hero_discards=(C("2s"), C("3s")),
        hero_can_prepare=True,
        hero_can_confirm=True,
        action_required=True,
    )
    pool = (C("Ks"), C("9h"), C("8h"), C("5h"), C("4h"), C("3h"), C("2h"), C("Ad"))
    return state, pool


def p95(values):
    ordered = sorted(values)
    return ordered[max(0, ceil(0.95 * len(ordered)) - 1)]


def main() -> None:
    state, pool = fixture()
    exact = evaluate_penultimate_normal_round_exact_last_chance(state, future_draw_pool=pool)
    truth = {v.action.key(): v.expected_value for v in exact.values}
    exact_best = {v.action.key() for v in exact.best_actions}

    seeds = tuple(2026081500 + i for i in range(20))
    print(f"seeds={len(seeds)} actions={len(exact.values)} branches={exact.chance_branches_per_action}")
    print(f"exact_best_value={exact.best_value:.12f}")

    for samples in (8, 16, 32):
        rmses = []
        max_abs_errors = []
        best_hits = 0
        covered = 0
        total_intervals = 0
        ci_widths = []
        started = time.perf_counter()

        for seed in seeds:
            mc = evaluate_penultimate_normal_round_monte_carlo(
                state,
                samples=samples,
                seed=seed,
                future_draw_pool=pool,
            )
            errors = []
            for value in mc.values:
                error = value.mean_value - truth[value.action.key()]
                errors.append(error)
                ci_widths.append(value.ci95_half_width)
                if abs(error) <= value.ci95_half_width + 1e-12:
                    covered += 1
                total_intervals += 1
            rmses.append(sqrt(sum(e * e for e in errors) / len(errors)))
            max_abs_errors.append(max(abs(e) for e in errors))
            if {v.action.key() for v in mc.best_actions} & exact_best:
                best_hits += 1

        elapsed = time.perf_counter() - started
        coverage = covered / total_intervals
        hit_rate = best_hits / len(seeds)
        print(
            f"samples={samples} "
            f"best_hit_rate={hit_rate:.6f} "
            f"mean_rmse={mean(rmses):.12f} p95_rmse={p95(rmses):.12f} "
            f"mean_max_abs={mean(max_abs_errors):.12f} p95_max_abs={p95(max_abs_errors):.12f} "
            f"ci95_empirical_coverage={coverage:.6f} mean_ci95_half={mean(ci_widths):.12f} "
            f"seconds={elapsed:.6f}"
        )

    print("PENULTIMATE MC MULTISEED CALIBRATION: PASS")


if __name__ == "__main__":
    main()
