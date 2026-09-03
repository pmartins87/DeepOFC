from __future__ import annotations

"""Build deterministic synthetic replay vectors for the native P3 bridge.

The fixture is intentionally a canonical-state replay, not pixel evidence.  It
drives one complete HU hand for each persistent button with P0 as the fixed
runtime Hero.  Every Hero decision includes the Python adapter's exact key
hash, canonical action, probability and physical placement action.
"""

import argparse
import hashlib
from pathlib import Path

from deepofc.sequential import HUSequentialNormalState
from deepofc.state import Card, OFCState, PlayerBoard, Row
from playable_p3_runtime_adapter import PersistentHUSeats, PlayableP3RuntimeAdapter

FIXTURE_SCHEMA = "openofc-playable-p3-native-synthetic-replay-v1"
P2_MANIFEST_SHA256 = "f10c079a61ba08832cfc334afb9c055e023dfc9c23a24140d02b2f7bd8413898"
NATIVE_MANIFEST_SHA256 = "ff880a76bce9885f19b7297952a9d182d0ba2c54e10681baa74937f66b4691bc"


def _card_value(card: Card) -> int:
    if card.joker_id is not None:
        return 51 + card.joker_id
    assert card.rank is not None and card.suit is not None
    return "cdhs".index(card.suit) * 13 + (card.rank - 2)


def _cards(cards: tuple[Card, ...]) -> str:
    return ",".join(str(_card_value(card)) for card in cards) or "-"


def _board_fields(board: PlayerBoard) -> tuple[str, str, str]:
    return (_cards(board.top), _cards(board.middle), _cards(board.bottom))


def _physical_action(decision) -> str:
    placements = sorted(
        (_card_value(placement.card), placement.row)
        for placement in decision.action.placements
    )
    placed = ",".join(
        f"{card}@{ {Row.TOP: 0, Row.MIDDLE: 1, Row.BOTTOM: 2}[row] }"
        for card, row in placements
    )
    discard = (
        "-"
        if decision.action.discard is None
        else str(_card_value(decision.action.discard))
    )
    return f"{placed}/{discard}"


def _state_fields(state: OFCState) -> list[str]:
    p0 = state.player(0)
    p1 = state.player(1)
    return [
        str(state.hero_chair),
        str(state.dealer_chair),
        str(state.acting_chair),
        str(state.round_index),
        "1" if state.hero_can_prepare else "0",
        str(p0.hidden_discard_count),
        str(p0.hidden_incoming_count),
        str(p1.hidden_discard_count),
        str(p1.hidden_incoming_count),
        *_board_fields(p0.board),
        *_board_fields(p1.board),
        _cards(state.hero_incoming),
        _cards(state.hero_discards),
    ]


def build_fixture(adapter: PlayableP3RuntimeAdapter) -> str:
    lines = [
        f"#{FIXTURE_SCHEMA}",
        f"#p2_manifest_sha256={P2_MANIFEST_SHA256}",
        f"#native_manifest_sha256={NATIVE_MANIFEST_SHA256}",
        "#synthetic_canonical_state_replay_not_pixel_or_live_evidence",
    ]
    seats = PersistentHUSeats(0, 1)
    case_index = 0
    for button, seed in ((0, 2026090500), (1, 2026090501)):
        game = HUSequentialNormalState.new(
            seed=seed,
            first_player=1 - button,
            dealer_chair=button,
        )
        first_state = True
        while not game.terminal:
            actor = game.acting_chair
            actor_observation = game.observation(actor)
            selected = adapter.select(actor_observation, seats)
            hero_observation = game.observation(0)
            decide = actor == 0
            command = ("R" if first_state else "O") + ("1" if decide else "0")
            expected = ["-", "-", "-", "-"]
            if decide:
                expected = [
                    str(selected.receipt["canonical_information_key_sha256"]),
                    selected.canonical_action_key,
                    repr(selected.selected_probability),
                    _physical_action(selected),
                ]
            lines.append(
                "|".join(
                    [command, str(case_index), *_state_fields(hero_observation.state), *expected]
                )
            )
            game = game.apply(selected.action)
            case_index += 1
            first_state = False
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p2-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    adapter = PlayableP3RuntimeAdapter.from_manifest(
        args.p2_manifest,
        expected_manifest_sha256=P2_MANIFEST_SHA256,
    )
    payload = build_fixture(adapter).encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(f"OPENOFC_PLAYABLE_P3_SYNTHETIC_REPLAY={args.output}")
    print(f"OPENOFC_PLAYABLE_P3_SYNTHETIC_REPLAY_SHA256={hashlib.sha256(payload).hexdigest()}")


if __name__ == "__main__":
    main()
