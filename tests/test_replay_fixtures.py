import json
from pathlib import Path

from deepofc.serde import state_from_dict
from deepofc.state import Card


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "replay"


def load_fixture(name: str):
    data = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return data, state_from_dict(data["state"])


def board_codes(state, chair: int) -> set[str]:
    return {c.code for c in state.player(chair).board.cards()}


def discard_codes(state) -> tuple[str, ...]:
    return tuple(c.code for c in state.hero_discards)


def test_all_gameplay_fixtures_parse_and_preserve_unique_known_cards():
    names = [
        "frame000468.json",
        "frame000482.json",
        "frame000512.json",
        "frame000528.json",
        "frame000543.json",
        "frame000560.json",
        "frame000568.json",
    ]
    for name in names:
        _, state = load_fixture(name)
        assert len(state.known_cards()) == len(set(state.known_cards()))
        assert state.mode == "joker_ultimate"
        assert len(state.players) == 2


def test_sampled_round_progression_has_expected_committed_counts():
    expected = {
        "frame000468.json": (0, 0, 0),
        "frame000482.json": (1, 5, 5),
        "frame000512.json": (2, 7, 7),
        "frame000528.json": (3, 9, 9),
        "frame000543.json": (3, 11, 9),
        "frame000560.json": (4, 13, 11),
        "frame000568.json": (4, 13, 11),
    }
    for name, (round_index, opp_count, hero_count) in expected.items():
        _, state = load_fixture(name)
        assert state.round_index == round_index
        assert state.player(0).board.filled_count() == opp_count
        assert state.player(1).board.filled_count() == hero_count


def test_opponent_turn_frames_separate_hidden_incoming_from_old_discards():
    expected = {
        "frame000468.json": (5, 0),
        "frame000482.json": (3, 0),
        "frame000512.json": (3, 1),
        "frame000528.json": (3, 2),
    }
    for name, (incoming, discards) in expected.items():
        _, state = load_fixture(name)
        opp = state.player(0)
        assert state.acting_chair == 0
        assert state.hero_can_prepare
        assert not state.hero_can_confirm
        assert not state.action_required
        assert opp.hidden_incoming_count == incoming
        assert opp.hidden_discard_count == discards


def test_frame_468_first_round_pending_shape_is_complete_but_not_confirmable_yet():
    _, state = load_fixture("frame000468.json")
    assert state.confirm_shape_is_legal()
    assert len(state.hero_pending) == 5
    assert not state.hero_can_confirm


def test_sampled_hero_round_transitions_match_visible_placements_and_discards():
    _, r2 = load_fixture("frame000482.json")
    _, r3 = load_fixture("frame000512.json")
    _, r4 = load_fixture("frame000528.json")
    _, r4_confirm = load_fixture("frame000543.json")
    _, r5 = load_fixture("frame000560.json")

    # Round 2: from incoming 7h/4d/5c, Hero commits 7h + 5c and discards 4d.
    assert board_codes(r3, 1) - board_codes(r2, 1) == {"7h", "5c"}
    assert discard_codes(r3) == ("4d",)

    # Round 3: from incoming 9h/4h/3d, Hero commits 9h + 4h and discards 3d.
    assert board_codes(r4, 1) - board_codes(r3, 1) == {"9h", "4h"}
    assert discard_codes(r4) == ("4d", "3d")

    # Round 4: frame 543 is the confirmed action candidate; next sampled round
    # proves Jh/Qc became committed and Ts became the new known discard.
    assert {p.card.code for p in r4_confirm.hero_pending} == {"Jh", "Qc"}
    assert r4_confirm.unassigned_incoming() == (Card.from_code("Ts"),)
    assert board_codes(r5, 1) - board_codes(r4, 1) == {"Jh", "Qc"}
    assert discard_codes(r5) == ("4d", "3d", "Ts")


def test_sampled_opponent_round_transitions_match_revealed_cards_and_hidden_discard_count():
    _, r2 = load_fixture("frame000482.json")
    _, r3 = load_fixture("frame000512.json")
    _, r4 = load_fixture("frame000528.json")
    _, r4_done = load_fixture("frame000543.json")
    _, r5_done = load_fixture("frame000560.json")

    assert board_codes(r3, 0) - board_codes(r2, 0) == {"7d", "2s"}
    assert r3.player(0).hidden_discard_count == r2.player(0).hidden_discard_count + 1

    assert board_codes(r4, 0) - board_codes(r3, 0) == {"Ac", "Qs"}
    assert r4.player(0).hidden_discard_count == r3.player(0).hidden_discard_count + 1

    assert board_codes(r4_done, 0) - board_codes(r4, 0) == {"7c", "5s"}
    assert r4_done.player(0).hidden_discard_count == r4.player(0).hidden_discard_count + 1
    assert r4_done.player(0).hidden_incoming_count == 0

    assert board_codes(r5_done, 0) - board_codes(r4_done, 0) == {"Kc", "Qd"}
    assert r5_done.player(0).hidden_discard_count == r4_done.player(0).hidden_discard_count + 1


def test_frame_512_tracks_tentative_nine_hearts_separately_from_committed_board():
    _, state = load_fixture("frame000512.json")
    hero = state.player(state.hero_chair)
    assert Card.from_code("9h") not in hero.board.cards()
    assert Card.from_code("9h") in {p.card for p in state.hero_pending}
    assert set(c.code for c in state.unassigned_incoming()) == {"4h", "3d"}
    assert tuple(c.code for c in state.hero_discards) == ("4d",)


def test_frame_543_is_a_legal_fourth_round_hero_confirm_state():
    raw, state = load_fixture("frame000543.json")
    assert raw["frame_sha256"] == "1c1e1f790299e639894d98a267dd71b577ae631a8c11bf14fe4c96bc0e1aa13a"
    assert state.round_index == 3
    assert state.hero_can_confirm
    assert state.confirm_shape_is_legal()
    assert state.unassigned_incoming() == (Card.from_code("Ts"),)
    opp = state.player(0)
    assert len(opp.board.top) == 3
    assert len(opp.board.middle) == 5
    assert len(opp.board.bottom) == 3
    assert opp.hidden_discard_count == 3
    assert opp.hidden_incoming_count == 0


def test_frame_560_to_568_is_only_tentative_hero_placement_change():
    _, before = load_fixture("frame000560.json")
    _, after = load_fixture("frame000568.json")
    assert before.player(0).board == after.player(0).board
    assert before.player(1).board == after.player(1).board
    assert before.hero_incoming == after.hero_incoming
    assert before.hero_discards == after.hero_discards
    assert before.hero_pending == ()
    assert len(after.hero_pending) == 2
    assert after.unassigned_incoming() == (Card.from_code("2d"),)
    assert after.confirm_shape_is_legal()


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
