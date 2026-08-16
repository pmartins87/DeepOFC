from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame


EXPECTED_SEQUENCES_PER_PLAYER = 405
EXPECTED_TERMINALS = 8 * EXPECTED_SEQUENCES_PER_PLAYER * EXPECTED_SEQUENCES_PER_PLAYER


def count_target_sequences(game, state, target: int) -> int:
    if state.terminal:
        return 1
    legal = state.legal_actions()
    if state.acting_chair == target:
        return sum(count_target_sequences(game, state.apply(action), target) for action in legal)
    # Opponent placements do not alter target row capacities/chance schedule in
    # this frozen fixture. Follow one legal opponent branch so the target's own
    # three-decision sequence count is measured through the real R4 engine.
    return count_target_sequences(game, state.apply(legal[0]), target)


def main() -> None:
    started = time.perf_counter()
    game = HUThreeRoundSequentialSubgame()
    build_seconds = time.perf_counter() - started

    sequence_counts = []
    started = time.perf_counter()
    for outcome in game.outcomes:
        root = game.initial_state(outcome)
        for player in (0, 1):
            count = count_target_sequences(game, root, player)
            sequence_counts.append(count)
            if count != EXPECTED_SEQUENCES_PER_PLAYER:
                raise SystemExit(
                    f"three-round player sequence count drift: outcome={outcome} "
                    f"player={player} count={count} expected={EXPECTED_SEQUENCES_PER_PLAYER}"
                )
    sequence_seconds = time.perf_counter() - started

    started = time.perf_counter()
    symmetry_checks = game.assert_terminal_swap_symmetry()
    symmetry_seconds = time.perf_counter() - started
    if symmetry_checks != EXPECTED_TERMINALS:
        raise SystemExit(
            f"three-round terminal count/symmetry mismatch: {symmetry_checks} vs {EXPECTED_TERMINALS}"
        )

    print(
        f"three_round_sequential_reference chance_outcomes={len(game.outcomes)} "
        f"sequences_per_player={EXPECTED_SEQUENCES_PER_PLAYER} "
        f"sequence_checks={len(sequence_counts)} terminals={EXPECTED_TERMINALS} "
        f"symmetry_checks={symmetry_checks} exact_reference_value=0"
    )
    print(
        f"timing build_seconds={build_seconds:.6f} "
        f"sequence_seconds={sequence_seconds:.6f} symmetry_seconds={symmetry_seconds:.6f}"
    )
    print("HU THREE-ROUND CANONICAL-SEQUENTIAL REFERENCE: PASS")


if __name__ == "__main__":
    main()
