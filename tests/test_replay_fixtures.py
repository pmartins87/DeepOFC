import json
from pathlib import Path

from deepofc.serde import state_from_dict
from deepofc.state import Card


ROOT = Path(__file__).resolve().parents[1]


def load_fixture(name: str):
    data = json.loads((ROOT / "fixtures" / "replay" / name).read_text(encoding="utf-8"))
    return data, state_from_dict(data["state"])


def test_frame_543_is_a_legal_fourth_round_hero_confirm_state():
    raw, state = load_fixture("frame000543.json")
    assert raw["frame_sha256"] == "1c1e1f790299e639894d98a267dd71b577ae631a8c11bf14fe4c96bc0e1aa13a"
    assert state.mode == "joker_ultimate"
    assert state.round_index == 3
    assert state.hero_can_confirm
    assert state.confirm_shape_is_legal()
    assert state.unassigned_incoming() == (Card.from_code("Ts"),)
    opp = state.player(0)
    assert len(opp.board.top) == 3
    assert len(opp.board.middle) == 5
    assert len(opp.board.bottom) == 3
    assert opp.hidden_discard_count == 3


def test_frame_568_is_a_legal_final_round_hero_confirm_state():
    raw, state = load_fixture("frame000568.json")
    assert raw["frame_sha256"] == "4fccc328f42788e519d70470541d0976dd22754997452b694a883eda73951321"
    assert state.round_index == 4
    assert state.confirm_shape_is_legal()
    assert state.unassigned_incoming() == (Card.from_code("2d"),)
    opp = state.player(0)
    assert opp.board.is_complete()
    assert opp.hidden_discard_count == 4


def test_fixture_proves_row_slot_identity_is_not_stable():
    _, state = load_fixture("frame000568.json")
    hero = state.player(state.hero_chair)
    assert set(c.code for c in hero.board.top) == {"Ks", "Jh", "4h"}
