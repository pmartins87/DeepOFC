from __future__ import annotations

"""Validate continuation-aware M5R BR intervals against exact tractable BR."""

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools/openofc_solver"
for candidate in (ROOT, TOOLS):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from deepofc.hu_three_round_br import exact_best_response
from deepofc.hu_three_round_sequential import HUThreeRoundSequentialSubgame
from deepofc.hu_three_round_sequential_v2 import HUThreeRoundSequentialSubgameV2
from deepofc.state import PlayerBoard
from engine import Board as EngineBoard, Card as EngineCard
from hu_continuation import (
    HUContinuationState,
    continuation_adjusted_terminal_utility,
    next_state_from_terminal_boards,
    swap_players,
)
from m5r_continuation_remainder_envelope import (
    candidate_next_states,
    p0_continuation_point_interval,
)
from m5r_continuation_transfer_manifest import (
    POSITIVE_THRESHOLD_HEX_BY_FAMILY,
    manifest_payload,
    manifest_sha256,
    structured_vector,
    vector_sha256,
    zero_vector,
)
from m5r_three_round_interval_bridge import conservative_three_round_br_interval

SCHEMA = "openofc-m5r-continuation-transfer-validation-cell-v1"
AUTHORITY = "M5R_TRACTABLE_CONTINUATION_BOUND_TRANSFER_VALIDATION_ONLY"
TOL = 1e-9


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _engine_board(board: PlayerBoard) -> EngineBoard:
    return EngineBoard(
        top=tuple(EngineCard.parse(card.code) for card in board.top),
        middle=tuple(EngineCard.parse(card.code) for card in board.middle),
        bottom=tuple(EngineCard.parse(card.code) for card in board.bottom),
    )


class _ContinuationAdjustedGame:
    """Delegate benchmark mechanics while replacing only terminal objective.

    Terminal objective conversion is cached by the complete persistent boards and
    dealer.  Each distinct terminal state is independently cross-checked once;
    repeated histories reuse exactly that validated value during the zero and
    positive interval traversals.
    """

    def __init__(self, base, values) -> None:
        self.base = base
        self.values = dict(values)
        self.outcomes = base.outcomes
        self.chance_probability = base.chance_probability
        self.terminal_calls = 0
        self.unique_terminal_crosschecks = 0
        self.next_state_candidate_checks = 0

    def __getattr__(self, name):
        return getattr(self.base, name)

    @lru_cache(maxsize=None)
    def _validated_terminal_value(
        self,
        p0_board: PlayerBoard,
        p1_board: PlayerBoard,
        dealer_chair: int,
    ) -> float:
        # Independent scorer/reference path: base benchmark raw points versus the
        # production Bellman terminal utility implementation.
        raw_reference_state = None
        board0 = _engine_board(p0_board)
        board1 = _engine_board(p1_board)
        current = HUContinuationState(
            button=int(dealer_chair),
            p0_fantasy_cards=0,
            p1_fantasy_cards=0,
        )
        nxt = next_state_from_terminal_boards(current, board0, board1)
        if nxt not in set(candidate_next_states(current)):
            raise AssertionError(
                f"exact terminal next state escaped conservative candidate set: {nxt.as_key()}"
            )
        if nxt not in self.values:
            raise AssertionError("exact terminal next state missing from continuation vector")

        # Construct a tiny state proxy only for the already-audited raw terminal
        # scorer.  Its terminal_u0 implementation reads terminal/boards only.
        class _RawState:
            terminal = True
            boards = (p0_board, p1_board)

        raw_reference_state = _RawState()
        raw_reference = float(self.base.terminal_u0(raw_reference_state))
        adjusted = continuation_adjusted_terminal_utility(
            current,
            board0,
            board1,
            self.values,
            update_player=0,
        )
        immediate_from_bellman_engine = adjusted - float(self.values[nxt])
        if abs(immediate_from_bellman_engine - raw_reference) > 1e-12:
            raise AssertionError(
                "independent raw scorer mismatch inside continuation validation: "
                f"{immediate_from_bellman_engine} vs {raw_reference}"
            )
        self.unique_terminal_crosschecks += 1
        self.next_state_candidate_checks += 1
        return float(adjusted)

    def terminal_u0(self, state) -> float:
        if not state.terminal:
            raise ValueError("terminal utility requires terminal state")
        self.terminal_calls += 1
        return self._validated_terminal_value(
            state.boards[0], state.boards[1], int(state.dealer_chair)
        )


def _game(family: str):
    if family == "three-round-v1":
        return HUThreeRoundSequentialSubgame()
    if family == "three-round-v2":
        return HUThreeRoundSequentialSubgameV2()
    raise ValueError(f"unsupported family: {family}")


def _assert_structured_vector_antisymmetry(values) -> int:
    checks = 0
    for state, value in values.items():
        partner = swap_players(state)
        if abs(float(value) + float(values[partner])) > 1e-15:
            raise AssertionError(
                f"structured continuation vector lost player-exchange antisymmetry at {state.as_key()}"
            )
        checks += 1
    return checks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", choices=("three-round-v1", "three-round-v2"), required=True)
    ap.add_argument("--player", type=int, choices=(0, 1), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    zero = zero_vector()
    values = structured_vector()
    antisymmetry_checks = _assert_structured_vector_antisymmetry(values)
    if any(value != 0.0 for value in zero.values()):
        raise AssertionError("zero continuation baseline is not identically zero")

    base = _game(args.family)
    game = _ContinuationAdjustedGame(base, values)
    profile = {}

    exact_started = time.perf_counter()
    exact = exact_best_response(game, profile, args.player)
    exact_seconds = time.perf_counter() - exact_started
    exact_terminal_calls = game.terminal_calls
    exact_unique_crosschecks = game.unique_terminal_crosschecks
    exact_next_state_checks = game.next_state_candidate_checks
    if exact_terminal_calls != exact.terminal_histories:
        raise AssertionError(
            "exact BR terminal accounting mismatch: "
            f"{exact_terminal_calls} vs {exact.terminal_histories}"
        )
    if exact_unique_crosschecks <= 0 or exact_next_state_checks != exact_unique_crosschecks:
        raise AssertionError("continuation terminal cross-check coverage is invalid")

    # The reduced benchmark mixes both dealer chairs. The bridge callback gets
    # boards but not that label, so union the two fixed-current NN envelopes.
    # This can widen the interval only; it cannot omit the actual branch value.
    @lru_cache(maxsize=None)
    def state_interval(p0_board: PlayerBoard, p1_board: PlayerBoard) -> tuple[float, float]:
        intervals = [
            p0_continuation_point_interval(
                HUContinuationState(button, 0, 0), values, p0_board, p1_board
            )
            for button in (0, 1)
        ]
        return min(lo for lo, _ in intervals), max(hi for _, hi in intervals)

    zero_started = time.perf_counter()
    zero_interval = conservative_three_round_br_interval(
        game,
        profile,
        args.player,
        prune_reach_threshold=0.0,
        p0_state_interval=state_interval,
    )
    zero_seconds = time.perf_counter() - zero_started

    threshold_hex = POSITIVE_THRESHOLD_HEX_BY_FAMILY[args.family]
    threshold = float.fromhex(threshold_hex)
    if threshold.hex() != threshold_hex:
        raise AssertionError("pre-frozen positive threshold changed binary identity")

    positive_started = time.perf_counter()
    positive = conservative_three_round_br_interval(
        game,
        profile,
        args.player,
        prune_reach_threshold=threshold,
        p0_state_interval=state_interval,
    )
    positive_seconds = time.perf_counter() - positive_started

    def contains(result) -> bool:
        return (
            result.lower_br_value - TOL
            <= exact.value
            <= result.upper_br_value + TOL
        )

    if not contains(zero_interval):
        raise SystemExit("structured-vector exact BR escaped zero-threshold interval")
    if abs(zero_interval.lower_br_value - exact.value) > TOL or abs(
        zero_interval.upper_br_value - exact.value
    ) > TOL:
        raise SystemExit("zero-threshold continuation interval did not reproduce exact BR")
    if not contains(positive):
        raise SystemExit("structured-vector exact BR escaped positive-threshold interval")
    if zero_interval.own_action_pruning_count != 0 or positive.own_action_pruning_count != 0:
        raise SystemExit("responding-player action pruning firewall violated")
    if positive.terminal_utility_evaluations >= exact.terminal_histories:
        raise SystemExit("positive reach breakpoint failed to reduce terminal work")

    unsigned = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "family": args.family,
        "player": args.player,
        "profile": "EMPTY_PROFILE_GAME_DEFINED_UNIFORM_FALLBACK",
        "manifest_sha256": manifest_sha256(),
        "manifest": manifest_payload(),
        "zero_vector_sha256": vector_sha256(zero),
        "structured_vector_sha256": vector_sha256(values),
        "structured_vector_antisymmetry_checks": antisymmetry_checks,
        "exact": {
            "br_value": float(exact.value),
            "terminal_histories": int(exact.terminal_histories),
            "responding_infosets": len(exact.choices),
            "terminal_calls": exact_terminal_calls,
            "unique_terminal_states_independently_crosschecked": exact_unique_crosschecks,
            "unique_exact_next_states_checked_against_conservative_set": exact_next_state_checks,
            "seconds": exact_seconds,
        },
        "zero_threshold": {
            "threshold": 0.0,
            "lower": zero_interval.lower_br_value,
            "upper": zero_interval.upper_br_value,
            "width": zero_interval.interval_width,
            "terminal_utility_evaluations": zero_interval.terminal_utility_evaluations,
            "own_action_pruning_count": zero_interval.own_action_pruning_count,
            "contains_exact_br": contains(zero_interval),
            "seconds": zero_seconds,
        },
        "positive_threshold": {
            "threshold": threshold,
            "threshold_hex": threshold_hex,
            "lower": positive.lower_br_value,
            "upper": positive.upper_br_value,
            "width": positive.interval_width,
            "terminal_utility_evaluations": positive.terminal_utility_evaluations,
            "terminal_work_fraction": (
                positive.terminal_utility_evaluations / exact.terminal_histories
            ),
            "pruned_opponent_branches": positive.pruned_opponent_branches,
            "state_local_envelope_calls": positive.state_local_envelope_calls,
            "own_action_pruning_count": positive.own_action_pruning_count,
            "contains_exact_br": contains(positive),
            "exact_minus_lower": exact.value - positive.lower_br_value,
            "upper_minus_exact": positive.upper_br_value - exact.value,
            "seconds": positive_seconds,
        },
        "cache": {
            "validated_terminal_cache_entries": game._validated_terminal_value.cache_info().currsize,
            "state_interval_cache_entries": state_interval.cache_info().currsize,
        },
        "decision": {
            "zero_vector_bound_reduces_to_raw_bound": True,
            "structured_vector_player_exchange_antisymmetry": True,
            "distinct_terminal_states_independently_raw_score_crosschecked": True,
            "exact_next_state_candidate_membership_crosschecked": True,
            "zero_threshold_exact": True,
            "positive_threshold_contains_exact_br": True,
            "positive_threshold_reduces_work": True,
            "own_action_pruning_count": 0,
            "tractable_continuation_bound_transfer_validated": True,
            "full_game_scalable_evaluator_validated": False,
            "production_certification_eligible": False,
            "real_routes_certified": 0,
        },
        "verdict": "PASS_M5R_CONTINUATION_TRANSFER_VALIDATION_CELL",
        "production_certification_eligible": False,
        "real_routes_certified": 0,
    }
    payload = dict(unsigned)
    payload["sha256"] = _sha(unsigned)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "family": args.family,
                "player": args.player,
                "exact_br": exact.value,
                "positive_width": positive.interval_width,
                "positive_terminal_work_fraction": (
                    positive.terminal_utility_evaluations / exact.terminal_histories
                ),
                "manifest_sha256": manifest_sha256(),
                "sha256": payload["sha256"],
                "verdict": payload["verdict"],
                "real_routes_certified": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
