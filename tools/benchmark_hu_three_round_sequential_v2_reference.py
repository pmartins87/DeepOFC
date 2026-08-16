from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2

EXPECTED_SEQUENCES_PER_PLAYER = 162
EXPECTED_TERMINALS = 32 * EXPECTED_SEQUENCES_PER_PLAYER * EXPECTED_SEQUENCES_PER_PLAYER


def count_target_sequences(game, state, target: int) -> int:
    if state.terminal:
        return 1
    info = game.info(state)
    legal = game.actions(info)
    if state.acting_chair == target:
        return sum(count_target_sequences(game, game.transition(state, action), target) for action in legal)
    return count_target_sequences(game, game.transition(state, legal[0]), target)


def main() -> None:
    game = HUThreeRoundSequentialSubgameV2()

    started = time.perf_counter()
    sequence_counts = []
    for outcome in game.outcomes:
        root = game.initial_state(outcome)
        for player in (0, 1):
            count = count_target_sequences(game, root, player)
            sequence_counts.append(count)
            if count != EXPECTED_SEQUENCES_PER_PLAYER:
                raise SystemExit(
                    f"V2 sequence-count drift: outcome={outcome} player={player} "
                    f"count={count} expected={EXPECTED_SEQUENCES_PER_PLAYER}"
                )
    sequence_seconds = time.perf_counter() - started

    started = time.perf_counter()
    symmetry_checks = game.assert_terminal_swap_symmetry()
    symmetry_seconds = time.perf_counter() - started
    if symmetry_checks != EXPECTED_TERMINALS:
        raise SystemExit(
            f"V2 terminal/symmetry mismatch: {symmetry_checks} vs {EXPECTED_TERMINALS}"
        )

    print(
        f"three_round_v2 chance_outcomes={len(game.outcomes)} "
        f"sequences_per_player={EXPECTED_SEQUENCES_PER_PLAYER} "
        f"sequence_checks={len(sequence_counts)} terminals={EXPECTED_TERMINALS} "
        f"symmetry_checks={symmetry_checks} exact_reference_value=0"
    )
    print(
        f"timing sequence_seconds={sequence_seconds:.6f} symmetry_seconds={symmetry_seconds:.6f}"
    )
    print("HU THREE-ROUND SEQUENTIAL V2 EXACT REFERENCE: PASS")


if __name__ == "__main__":
    main()
