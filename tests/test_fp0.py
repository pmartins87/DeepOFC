from deepofc.fp0 import prepare_fp0_turn
from deepofc.runtime_plan import strategic_decision_fingerprint
from deepofc.state import Card, OFCState, PlayerBoard, PlayerState


def C(code: str) -> Card:
    return Card.from_code(code)


def test_prepare_fp0_turn_binds_baseline_action_to_current_canonical_state():
    state = OFCState(
        players=(
            PlayerState(chair=0),
            PlayerState(
                chair=1,
                board=PlayerBoard(
                    top=(C("As"),),
                    middle=(C("Kh"), C("Qh")),
                    bottom=(C("8c"), C("7c")),
                ),
            ),
        ),
        hero_chair=1,
        dealer_chair=1,
        acting_chair=1,
        round_index=1,
        hero_incoming=(C("Jd"), C("Ts"), C("9h")),
        hero_can_prepare=True,
    )

    prepared = prepare_fp0_turn(state)

    assert prepared.plan.decision_fingerprint == strategic_decision_fingerprint(state)
    assert prepared.plan.fantasy is False
    assert len(prepared.plan.target_placements) == 2
    assert len(prepared.plan.unused_cards) == 1
    assert prepared.decision.action.key() == (
        tuple(sorted((p.card_code, p.row.value) for p in prepared.plan.target_placements)),
        prepared.plan.unused_cards[0],
    )
