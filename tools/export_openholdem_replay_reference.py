from __future__ import annotations

"""Export canonical replay/contract fixtures into a tiny line protocol.

The consumer is the native C++ COFCReconstructor self-test in the OpenHoldem
`deepofc` branch. This keeps the cross-language equality gate independent of a
JSON library on the legacy C++ side while preserving the Python DeepOFC model
as the source of truth.

The seven original entries are screenshot-backed normal-play fixtures. The
final Fantasy entry is explicitly synthetic: it freezes already source-backed
state semantics before the separate real-pixel Fantasy tablemap gate exists.
"""

import argparse
import json
from pathlib import Path

from deepofc.serde import state_from_dict
from deepofc.state import Row


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "replay"
SEQUENCE = [
    "frame000468.json",
    "frame000482.json",
    "frame000512.json",
    "frame000528.json",
    "frame000543.json",
    "frame000560.json",
    "frame000568.json",
    "fantasy_contract_17_prepare.json",
]

RANK_INDEX = {r: i for i, r in enumerate("23456789TJQKA")}
SUIT_INDEX = {"h": 0, "d": 1, "c": 2, "s": 3}
ROW_INDEX = {Row.TOP: 0, Row.MIDDLE: 1, Row.BOTTOM: 2}


def oh_value(card) -> int:
    if card.is_joker:
        return 51 + int(card.joker_id)
    code = card.code
    return SUIT_INDEX[code[1]] * 13 + RANK_INDEX[code[0]]


def csv_cards(cards) -> str:
    values = sorted(oh_value(c) for c in cards)
    return ",".join(str(v) for v in values) if values else "-"


def raw_from_golden(golden):
    hero = golden.player(golden.hero_chair)
    visual = {row: list(hero.board.row(row)) for row in Row}
    for pending in golden.hero_pending:
        visual[pending.row].append(pending.card)
    pending_cards = {p.card for p in golden.hero_pending}
    loose = tuple(c for c in golden.hero_incoming if c not in pending_cards)
    return visual, loose


def expected_snapshot(golden) -> str:
    players = []
    for p in golden.players:
        players.append(
            {
                "chair": p.chair,
                "occupied": True,
                "source_chair": p.chair,
                "top": sorted(oh_value(c) for c in p.board.top),
                "middle": sorted(oh_value(c) for c in p.board.middle),
                "bottom": sorted(oh_value(c) for c in p.board.bottom),
                "hidden_incoming_count": p.hidden_incoming_count,
                "hidden_discard_count": p.hidden_discard_count,
                "fantasy": p.fantasy,
                "sitting_out": p.sitting_out,
            }
        )

    incoming_values = sorted(oh_value(c) for c in golden.hero_incoming)
    pending = []
    for p in golden.hero_pending:
        value = oh_value(p.card)
        pending.append(
            {
                "incoming_index": incoming_values.index(value),
                "row": ROW_INDEX[p.row],
                "_value": value,
            }
        )
    pending.sort(key=lambda x: (x["_value"], x["row"]))
    for p in pending:
        del p["_value"]

    payload = {
        "schema_version": 1,
        "valid": True,
        "player_count": len(golden.players),
        "hero_chair": golden.hero_chair,
        "dealer_chair": golden.dealer_chair,
        "acting_chair": golden.acting_chair,
        "round_index": golden.round_index,
        "players": players,
        "hero_incoming": incoming_values,
        "hero_discards": sorted(oh_value(c) for c in golden.hero_discards),
        "pending": pending,
        "hero_can_prepare": golden.hero_can_prepare,
        "hero_can_confirm": golden.hero_can_confirm,
        "action_required": golden.action_required,
    }
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def export(out: Path) -> None:
    lines: list[str] = ["DEEPOFC_OPENHOLDEM_REPLAY_REFERENCE|2"]
    for name in SEQUENCE:
        data = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
        golden = state_from_dict(data["state"])
        hero_visual, loose = raw_from_golden(golden)

        # The original supplied screenshots visibly show the gold Confirm
        # control during both opponent and Hero turns. Legal confirmation is
        # derived from actor. The synthetic Fantasy contract uses the same raw
        # safety convention: visible Confirm is not permission to commit early.
        lines.append(f"FRAME|{name}")
        lines.append(
            "META|{}|{}|{}|{}|{}|{}|{}".format(
                len(golden.players),
                golden.hero_chair,
                golden.dealer_chair,
                golden.acting_chair,
                golden.round_index,
                1 if golden.hero_can_prepare else 0,
                1,  # raw confirm_visible
            )
        )
        for p in golden.players:
            board = p.board
            if p.chair == golden.hero_chair:
                top = tuple(hero_visual[Row.TOP])
                middle = tuple(hero_visual[Row.MIDDLE])
                bottom = tuple(hero_visual[Row.BOTTOM])
            else:
                top, middle, bottom = board.top, board.middle, board.bottom
            lines.append(
                "PLAYER|{}|{}|{}|{}|{}|{}|{}|{}".format(
                    p.chair,
                    p.hidden_incoming_count,
                    p.hidden_discard_count,
                    1 if p.fantasy else 0,
                    1 if p.sitting_out else 0,
                    csv_cards(top),
                    csv_cards(middle),
                    csv_cards(bottom),
                )
            )
        lines.append(f"LOOSE|{csv_cards(loose)}")
        lines.append(f"DISCARDS|{csv_cards(golden.hero_discards)}")
        lines.append(f"EXPECTED|{expected_snapshot(golden)}")
        lines.append("END")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    export(args.out)
    print(args.out)


if __name__ == "__main__":
    main()
