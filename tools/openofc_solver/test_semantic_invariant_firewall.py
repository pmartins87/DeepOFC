from __future__ import annotations

"""Pre-heavy-training semantic invariants for the KKPoker HU target.

This gate was added after auditing the external `ainaosyusi/ofc-pineapple-ai`
postmortem in which 250M+ RL steps were invalidated by an Ace-ordering bug.
The purpose here is broader than reproducing that one bug: fail before expensive
training whenever ranking, Joker, scoring, Fantasy, action, or information-set
semantics drift.
"""

from engine import (
    Board,
    Card,
    CAT_FLUSH,
    CAT_FULL_HOUSE,
    CAT_HIGH,
    CAT_PAIR,
    CAT_QUADS,
    CAT_STRAIGHT,
    CAT_STRAIGHT_FLUSH,
    CAT_TRIPS,
    CAT_TWO_PAIR,
    ROW_BOTTOM,
    _eval_regular,
    fantasy_award_from_top,
    legal_actions,
    parse_cards,
    resolve_board,
    score_heads_up,
)
from fantasy_transition import (
    VARIANT_ULTIMATE,
    qualifies_for_refantasy,
    transition_from_resolved,
)
from strategic_cfr import DealPlan, HUState, information_state_key


def C(text: str) -> Card:
    return Card.parse(text)


def B(top: str, middle: str, bottom: str) -> Board:
    return Board(parse_cards(top), parse_cards(middle), parse_cards(bottom))


def _pair3(rank: str):
    kicker = "K" if rank == "A" else "A"
    return _eval_regular((C(rank + "c"), C(rank + "d"), C(kicker + "h")))


def _pair5(rank: str):
    kicker_ranks = [r for r in "AKQJT98765432" if r != rank][:3]
    return _eval_regular(
        (
            C(rank + "c"),
            C(rank + "d"),
            C(kicker_ranks[0] + "h"),
            C(kicker_ranks[1] + "s"),
            C(kicker_ranks[2] + "c"),
        )
    )


def test_ace_and_all_pair_rank_orderings_are_monotone() -> None:
    descending = "AKQJT98765432"
    top = [_pair3(rank) for rank in descending]
    five = [_pair5(rank) for rank in descending]
    assert all(top[i] > top[i + 1] for i in range(len(top) - 1))
    assert all(five[i] > five[i + 1] for i in range(len(five) - 1))
    # Explicit regression for the external ACE=0 catastrophe.
    assert _pair3("A") > _pair3("2")
    assert _pair5("A") > _pair5("2")


def test_ace_high_and_pair_kicker_ordering() -> None:
    a_high = _eval_regular(parse_cards("Ac Qd 9h"))
    k_high = _eval_regular(parse_cards("Kc Qh 9d"))
    assert a_high.category == CAT_HIGH
    assert a_high > k_high

    kk_a = _eval_regular(parse_cards("Kc Kd Ah"))
    kk_q = _eval_regular(parse_cards("Kh Ks Qd"))
    assert kk_a.category == CAT_PAIR
    assert kk_a > kk_q


def test_five_card_category_order_is_strict() -> None:
    hands = (
        _eval_regular(parse_cards("Ac Kd 9h 7s 3c")),             # high
        _eval_regular(parse_cards("Ac Ad 9h 7s 3c")),             # pair
        _eval_regular(parse_cards("Ac Ad 9h 9s 3c")),             # two pair
        _eval_regular(parse_cards("Ac Ad Ah 9s 3c")),             # trips
        _eval_regular(parse_cards("2c 3d 4h 5s 6c")),             # straight
        _eval_regular(parse_cards("Ac Jc 9c 6c 3c")),             # flush
        _eval_regular(parse_cards("Ac Ad Ah 9s 9c")),             # full house
        _eval_regular(parse_cards("Ac Ad Ah As 9c")),             # quads
        _eval_regular(parse_cards("9c Tc Jc Qc Kc")),             # straight flush
    )
    assert tuple(hand.category for hand in hands) == (
        CAT_HIGH,
        CAT_PAIR,
        CAT_TWO_PAIR,
        CAT_TRIPS,
        CAT_STRAIGHT,
        CAT_FLUSH,
        CAT_FULL_HOUSE,
        CAT_QUADS,
        CAT_STRAIGHT_FLUSH,
    )
    assert all(hands[i] < hands[i + 1] for i in range(len(hands) - 1))


def test_wheel_and_broadway_boundaries() -> None:
    wheel = _eval_regular(parse_cards("Ac 2d 3h 4s 5c"))
    six_high = _eval_regular(parse_cards("2c 3d 4h 5s 6c"))
    broadway = _eval_regular(parse_cards("Tc Jd Qh Ks Ac"))
    assert wheel.category == CAT_STRAIGHT and wheel.tie == (5,)
    assert six_high.category == CAT_STRAIGHT and six_high.tie == (6,)
    assert broadway.category == CAT_STRAIGHT and broadway.tie == (14,)
    assert wheel < six_high < broadway


def test_two_jokers_can_complete_royal_flush() -> None:
    board = B(
        "2c 2d 3h",
        "4c 4d 5h 6s 7d",
        "Tc Jc Qc JK1 JK2",
    )
    resolved = resolve_board(board)
    assert resolved is not None
    bottom = resolved.ranks[ROW_BOTTOM]
    assert bottom.category == CAT_STRAIGHT_FLUSH
    assert bottom.royal
    assert bottom.tie == (14,)


def test_joker_substitution_is_row_local_even_if_represented_card_is_elsewhere() -> None:
    # Ac is physically present in Top.  Under the frozen KKPoker row-local
    # semantics, the Bottom Joker may still be interpreted as Ac when that is
    # the strongest row-local poker interpretation.
    board = B(
        "Ac 8d 7h",
        "2c 2d 3h 4s 5d",
        "Tc Jc Qc Kc JK1",
    )
    resolved = resolve_board(board)
    assert resolved is not None
    bottom = resolved.ranks[ROW_BOTTOM]
    assert bottom.category == CAT_STRAIGHT_FLUSH
    assert bottom.royal


def test_target_fantasy_mapping_is_exact_14_15_16_17() -> None:
    assert fantasy_award_from_top(_pair3("Q")) == 14
    assert fantasy_award_from_top(_pair3("K")) == 15
    assert fantasy_award_from_top(_pair3("A")) == 16
    aaa = _eval_regular(parse_cards("Ac Ad Ah"))
    assert aaa.category == CAT_TRIPS
    assert fantasy_award_from_top(aaa) == 17


def test_middle_full_house_alone_does_not_refantasy_in_target_ultimate_rules() -> None:
    # This explicitly protects a target-rule difference found in external
    # projects that use Middle full-house-or-better as a stay condition.
    board = B(
        "2c 2d 3h",
        "6c 6d 6h 5c 5d",
        "7c 7d 7h 4c 4d",
    )
    resolved = resolve_board(board)
    assert resolved is not None
    assert resolved.ranks[1].category == CAT_FULL_HOUSE
    assert resolved.ranks[2].category == CAT_FULL_HOUSE
    assert not qualifies_for_refantasy(resolved)
    transition = transition_from_resolved(
        resolved,
        current_fantasy_cards=16,
        variant=VARIANT_ULTIMATE,
    )
    assert not transition.refantasy
    assert transition.next_cards == 0


def test_heads_up_terminal_scoring_is_antisymmetric() -> None:
    p0 = B("Qc Qd 2h", "2c 3c 4c 5c 6c", "9h Th Jh Qh Kh")
    p1 = B("Jc Jd 3h", "4h 5d 6h 7d 8c", "9c Tc Jh Qs Kd")
    forward = score_heads_up(p0, p1)
    reverse = score_heads_up(p1, p0)
    assert forward.points == -reverse.points
    assert forward.row_points == tuple(-x for x in reverse.row_points)
    assert forward.scoop == -reverse.scoop
    assert forward.royalty_diff == -reverse.royalty_diff


def test_opening_and_pineapple_action_semantics_are_not_aliased() -> None:
    opening_cards = parse_cards("Ac Kd Qh Js Tc")
    opening = legal_actions(Board(), opening_cards, 0)
    assert len(opening) == 232
    assert all(action.discard_index is None for action in opening)
    assert all(len(action.placements) == 5 for action in opening)
    assert all({index for index, _row in action.placements} == set(range(5)) for action in opening)

    board = B("Ac", "Kd Qd", "2c 3c")
    draw = parse_cards("7h 8h 9h")
    later = legal_actions(board, draw, 1)
    assert len(later) == 27
    for action in later:
        assert action.discard_index in (0, 1, 2)
        assert len(action.placements) == 2
        placed = {index for index, _row in action.placements}
        assert placed | {action.discard_index} == {0, 1, 2}
        assert action.discard_index not in placed


def _plan(opp_opening: str) -> DealPlan:
    return DealPlan(
        opening=(
            parse_cards("Ac Kd Qh Js Tc"),
            parse_cards(opp_opening),
        ),
        rounds=(
            (parse_cards("2c 3c 4c"), parse_cards("2d 3d 4d")),
            (parse_cards("5c 6c 7c"), parse_cards("5d 6d 7d")),
            (parse_cards("8c 9c Tc"), parse_cards("8d 9d Td")),
            (parse_cards("Jc Qc Kc"), parse_cards("Jh Qh Kh")),
        ),
    )


def test_information_state_never_exposes_opponent_private_packet() -> None:
    left = HUState(plan=_plan("Ah Kh Qd Jd 9s"))
    right = HUState(plan=_plan("As Ks Qs 9h 8h"))
    assert information_state_key(left) == information_state_key(right)


def test_information_state_hides_opponent_discards_but_remembers_own_discards() -> None:
    plan = _plan("Ah Kh Qd Jd 9s")
    base = dict(plan=plan, round_index=1, actor=1, boards=(Board(), Board()))
    a = HUState(**base, discards=((C("2s"),), (C("3s"),)))
    b = HUState(**base, discards=((C("4s"),), (C("3s"),)))
    c = HUState(**base, discards=((C("2s"),), (C("5s"),)))
    assert information_state_key(a) == information_state_key(b)
    assert information_state_key(a) != information_state_key(c)
