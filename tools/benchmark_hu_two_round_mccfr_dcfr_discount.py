from __future__ import annotations

from pathlib import Path
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_mccfr_dcfr import TwoRoundExternalSamplingLazyDCFR


def sequential(value: float, start: int, end: int, exponent: float) -> float:
    out = float(value)
    for t in range(start, end + 1):
        power = float(t) ** exponent
        out *= power / (power + 1.0)
    return out


def main() -> None:
    game = HUTwoRoundSubgame()
    solver = TwoRoundExternalSamplingLazyDCFR(game, seed=7)
    info = next(iter(game.info_actions))
    actions = game.actions(info)
    if len(actions) < 3:
        raise SystemExit("discount fixture needs at least three actions")

    solver.regrets[info][actions[0]] = 3.25
    solver.regrets[info][actions[1]] = -7.5
    solver.regrets[info][actions[2]] = 0.125
    for action in actions[3:]:
        solver.regrets[info][action] = 0.0
    solver.last_discounted[info] = 2

    before_distribution = super(TwoRoundExternalSamplingLazyDCFR, solver)._distribution(info)
    expected = {}
    for action, value in solver.regrets[info].items():
        exponent = solver.alpha if value >= 0.0 else solver.beta
        expected[action] = sequential(value, 3, 37, exponent)

    solver._discount_to(info, 37)
    worst = max(abs(solver.regrets[info][a] - expected[a]) for a in actions)
    if worst > 1e-12:
        raise SystemExit(f"collapsed lazy discount mismatch: {worst}")
    if solver.last_discounted[info] != 37:
        raise SystemExit("lazy discount timestamp did not advance")

    after_distribution = super(TwoRoundExternalSamplingLazyDCFR, solver)._distribution(info)
    strategy_error = max(
        abs(before_distribution[a] - after_distribution[a]) for a in actions
    )
    if strategy_error > 1e-12:
        raise SystemExit(
            "regret-matching behavior changed under pure skipped DCFR discount: "
            f"{strategy_error}"
        )

    # Re-applying the same target must be exactly idempotent.
    frozen = dict(solver.regrets[info])
    solver._discount_to(info, 37)
    if any(solver.regrets[info][a] != frozen[a] for a in actions):
        raise SystemExit("same-target lazy discount was not idempotent")

    print(
        f"lazy_dcfr_discount actions={len(actions)} interval=3..37 "
        f"max_abs_regret_error={worst:.18e} "
        f"max_abs_strategy_error={strategy_error:.18e}"
    )
    print("HU TWO-ROUND LAZY DCFR DISCOUNT: PASS")


if __name__ == "__main__":
    main()
