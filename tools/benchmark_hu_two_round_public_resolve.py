from __future__ import annotations

from pathlib import Path
import math
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepofc.hu_two_round import HUTwoRoundSubgame
from deepofc.hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR
from deepofc.hu_two_round_resolve import (
    Round4PublicDCFR,
    build_round4_public_subgames,
)


def main() -> None:
    game = HUTwoRoundSubgame()
    blueprint_solver = TwoRoundExternalSamplingMCCFR(game, seed=20260815)

    started = time.perf_counter()
    blueprint_solver.run(5_000)
    blueprint_train_seconds = time.perf_counter() - started
    blueprint = blueprint_solver.current_profile()
    full_ev = game.expected_u0(blueprint)

    started = time.perf_counter()
    subgames = build_round4_public_subgames(game, blueprint)
    build_seconds = time.perf_counter() - started

    public_mass = sum(s.public_reach_probability for s in subgames.values())
    reconstructed_ev = sum(
        sub.public_reach_probability * sub.expected_u0(blueprint)
        for sub in subgames.values()
    )
    decomposition_error = abs(reconstructed_ev - full_ev)
    if abs(public_mass - 1.0) > 1e-10:
        raise SystemExit(f"public reach mass drift: {public_mass}")
    if decomposition_error > 1e-10:
        raise SystemExit(
            f"public continuation decomposition changed blueprint EV: {reconstructed_ev} vs {full_ev}"
        )

    # Public-key privacy audit on every reachable hidden history. In addition to
    # checking that no private card is literally stored in the public key, count
    # whether the SAME public state is compatible with multiple distinct round-3
    # discard pairs. The latter distinguishes syntactic privacy from strategic
    # ambiguity under the reduced chance support.
    privacy_checks = 0
    max_hidden_histories = 0
    ambiguous_discard_states = 0
    max_discard_pairs_per_public_state = 0
    for state, sub in subgames.items():
        max_hidden_histories = max(max_hidden_histories, len(sub.histories))
        state_codes = {card for card, _row in state.first_round3_public}
        state_codes.update(card for card, _row in state.second_round3_public)
        discard_pairs: set[tuple[str, str]] = set()
        for history in sub.histories:
            first_discard = history.first_round3_action.discard
            second_discard = history.second_round3_action.discard
            assert first_discard is not None and second_discard is not None
            discard_pairs.add((first_discard.code, second_discard.code))
            if first_discard.code in {card for card, _ in state.first_round3_public}:
                raise SystemExit("first discard leaked into public placement key")
            if second_discard.code in {card for card, _ in state.second_round3_public}:
                raise SystemExit("second discard leaked into public placement key")
            for card in history.outcome.round4_hand0 + history.outcome.round4_hand1:
                if card.code in state_codes:
                    raise SystemExit("future round4 private card leaked into round3 public key")
            privacy_checks += 1
        max_discard_pairs_per_public_state = max(
            max_discard_pairs_per_public_state, len(discard_pairs)
        )
        if len(discard_pairs) > 1:
            ambiguous_discard_states += 1

    target = max(
        subgames.values(),
        key=lambda sub: (sub.public_reach_probability, len(sub.histories)),
    )
    before_ev = target.expected_u0(blueprint)
    before_exp = target.exploitability(blueprint)

    resolver = Round4PublicDCFR(target)
    started = time.perf_counter()
    resolver.run(256)
    resolve_seconds = time.perf_counter() - started
    resolved = resolver.average_profile()
    after_ev = target.expected_u0(resolved)
    after_exp = target.exploitability(resolved)

    if not all(math.isfinite(x) for x in (before_ev, before_exp, after_ev, after_exp)):
        raise SystemExit("public resolver produced non-finite diagnostics")
    if after_exp >= before_exp:
        raise SystemExit(
            "public DCFR failed to reduce exact continuation exploitability: "
            f"before={before_exp} after={after_exp}"
        )

    print(
        f"blueprint iterations=5000 train_seconds={blueprint_train_seconds:.6f} "
        f"full_expected_u0={full_ev:.12f}"
    )
    print(
        f"public_decomposition states={len(subgames)} mass={public_mass:.12f} "
        f"reconstructed_ev={reconstructed_ev:.12f} error={decomposition_error:.18e} "
        f"privacy_checks={privacy_checks} max_hidden_histories={max_hidden_histories} "
        f"ambiguous_discard_states={ambiguous_discard_states} "
        f"max_discard_pairs={max_discard_pairs_per_public_state} "
        f"build_seconds={build_seconds:.6f}"
    )
    print(
        f"target reach={target.public_reach_probability:.12f} "
        f"hidden_histories={len(target.histories)} infosets={len(target.info_actions)} "
        f"first_player={target.public_state.first_player}"
    )
    print(
        f"target_blueprint expected_u0={before_ev:.12f} exploitability={before_exp:.12f}"
    )
    print(
        f"target_resolved iterations=256 expected_u0={after_ev:.12f} "
        f"exploitability={after_exp:.12f} resolve_seconds={resolve_seconds:.6f}"
    )
    print("HU TWO-ROUND PUBLIC-STATE ROUND4 RE-SOLVE: PASS")


if __name__ == "__main__":
    main()
