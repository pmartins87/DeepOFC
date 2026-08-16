from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_three_round_br import exact_best_response, exact_value_of_pure_response
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame


EXPECTED_TERMINALS = 1_312_200
EXPECTED_PURE_REPLAY_TERMINALS = 8 * 405


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    args = ap.parse_args()

    game = HUThreeRoundSequentialSubgame()
    uniform = {}

    started = time.perf_counter()
    response = exact_best_response(game, uniform, args.player)
    br_seconds = time.perf_counter() - started
    if response.terminal_histories != EXPECTED_TERMINALS:
        raise SystemExit(
            f"BR{args.player} terminal coverage mismatch: "
            f"{response.terminal_histories} vs {EXPECTED_TERMINALS}"
        )

    started = time.perf_counter()
    replay, replay_terminals = exact_value_of_pure_response(game, uniform, response)
    replay_seconds = time.perf_counter() - started
    if replay_terminals != EXPECTED_PURE_REPLAY_TERMINALS:
        raise SystemExit(
            f"BR{args.player} pure replay work mismatch: "
            f"{replay_terminals} vs {EXPECTED_PURE_REPLAY_TERMINALS}"
        )
    if abs(response.value - replay) > 1e-10:
        raise SystemExit(
            f"BR{args.player} pure replay mismatch: {response.value} vs {replay}"
        )

    print(
        f"player={args.player} exact_br={response.value:.12f} "
        f"exploitability_contribution={0.5*response.value:.12f} "
        f"infosets={len(response.choices)} terminal_histories={response.terminal_histories} "
        f"br_seconds={br_seconds:.6f}"
    )
    print(
        f"player={args.player} independent_pure_replay={replay:.12f} "
        f"pure_replay_terminals={replay_terminals} replay_seconds={replay_seconds:.6f}"
    )
    print(f"HU THREE-ROUND EXACT BR PLAYER {args.player}: PASS")


if __name__ == "__main__":
    main()
