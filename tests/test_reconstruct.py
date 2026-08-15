import json
from pathlib import Path

import pytest

from deepofc.observation import RawOFCObservation, RawPlayerObservation
from deepofc.reconstruct import ReconstructionError, reconstruct_observation
from deepofc.serde import state_from_dict
from deepofc.state import PlayerBoard, Row


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
]


def load_golden(name: str):
    data = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return state_from_dict(data["state"])


def raw_from_golden(golden):
    hero = golden.player(golden.hero_chair)
    visual = {row: list(hero.board.row(row)) for row in Row}
    for p in golden.hero_pending:
        visual[p.row].append(p.card)
    hero_visual = PlayerBoard(
        top=tuple(visual[Row.TOP]),
        middle=tuple(visual[Row.MIDDLE]),
        bottom=tuple(visual[Row.BOTTOM]),
    )
    pending_cards = {p.card for p in golden.hero_pending}
    loose = tuple(c for c in golden.hero_incoming if c not in pending_cards)

    players = []
    for p in golden.players:
        players.append(
            RawPlayerObservation(
                chair=p.chair,
                visual_board=hero_visual if p.chair == golden.hero_chair else p.board,
                hidden_incoming_count=p.hidden_incoming_count,
                hidden_discard_count=p.hidden_discard_count,
                name=p.name,
                fantasy=p.fantasy,
                sitting_out=p.sitting_out,
            )
        )
    # The supplied gameplay screenshots visibly show the gold Confirm control
    # even while Oxy87's timer is active. Safe commit is derived separately from
    # acting order by the reconstructor.
    return RawOFCObservation(
        players=tuple(players),
        hero_chair=golden.hero_chair,
        dealer_chair=golden.dealer_chair,
        acting_chair=golden.acting_chair,
        round_index=golden.round_index,
        hero_loose_cards=loose,
        hero_discard_tracker=golden.hero_discards,
        hero_can_prepare=golden.hero_can_prepare,
        confirm_visible=True,
        mode=golden.mode,
    )


def board_signature(board):
    return {
        row: frozenset(c.code for c in board.row(row))
        for row in Row
    }


def state_signature(state):
    return {
        "round": state.round_index,
        "actor": state.acting_chair,
        "dealer": state.dealer_chair,
        "hero": state.hero_chair,
        "boards": {p.chair: board_signature(p.board) for p in state.players},
        "hidden_incoming": {p.chair: p.hidden_incoming_count for p in state.players},
        "hidden_discards": {p.chair: p.hidden_discard_count for p in state.players},
        "incoming": frozenset(c.code for c in state.hero_incoming),
        "discards": frozenset(c.code for c in state.hero_discards),
        "pending": frozenset((p.card.code, p.row.value) for p in state.hero_pending),
        "prepare": state.hero_can_prepare,
        "confirm": state.hero_can_confirm,
        "required": state.action_required,
        "mode": state.mode,
    }


def test_stateful_reconstructor_reproduces_all_seven_golden_gameplay_frames():
    previous = None
    for name in SEQUENCE:
        golden = load_golden(name)
        raw = raw_from_golden(golden)
        rebuilt = reconstruct_observation(raw, previous)
        assert state_signature(rebuilt) == state_signature(golden), name
        previous = rebuilt


def test_visible_confirm_does_not_override_opponent_action_order():
    golden = load_golden("frame000512.json")
    raw = raw_from_golden(golden)
    assert raw.confirm_visible
    previous = reconstruct_observation(raw_from_golden(load_golden("frame000468.json")))
    previous = reconstruct_observation(raw_from_golden(load_golden("frame000482.json")), previous)
    rebuilt = reconstruct_observation(raw, previous)
    assert rebuilt.acting_chair != rebuilt.hero_chair
    assert not rebuilt.hero_can_confirm
    assert not rebuilt.action_required


def test_midhand_attach_fails_closed_without_history():
    golden = load_golden("frame000528.json")
    raw = raw_from_golden(golden)
    with pytest.raises(ReconstructionError, match="mid-hand"):
        reconstruct_observation(raw, previous=None)


def test_same_round_incoming_identity_change_is_rejected():
    first = load_golden("frame000560.json")
    previous = reconstruct_observation(raw_from_golden(load_golden("frame000468.json")))
    for name in SEQUENCE[1:6]:
        previous = reconstruct_observation(raw_from_golden(load_golden(name)), previous)
    assert state_signature(previous) == state_signature(first)

    bad_raw = raw_from_golden(load_golden("frame000568.json"))
    # Replace the only loose card (2d) with an impossible unrelated card while
    # keeping the same round. The reconstructor must detect identity drift.
    from deepofc.state import Card
    bad_raw = RawOFCObservation(
        players=bad_raw.players,
        hero_chair=bad_raw.hero_chair,
        dealer_chair=bad_raw.dealer_chair,
        acting_chair=bad_raw.acting_chair,
        round_index=bad_raw.round_index,
        hero_loose_cards=(Card.from_code("3c"),),
        hero_discard_tracker=bad_raw.hero_discard_tracker,
        hero_can_prepare=bad_raw.hero_can_prepare,
        confirm_visible=bad_raw.confirm_visible,
        mode=bad_raw.mode,
    )
    with pytest.raises(ReconstructionError, match="identities changed"):
        reconstruct_observation(bad_raw, previous)
