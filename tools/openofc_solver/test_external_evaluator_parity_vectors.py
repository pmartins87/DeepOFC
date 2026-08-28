from __future__ import annotations

"""External evaluator shadow-parity vectors.

This is research evidence only.  It does not vendor or execute third-party code.
The vectors are independently expressed against the frozen DeepOFC target
semantics and pinned to the public external source revisions that motivated
them.

Primary source:
  ainaosyusi/ofc-pineapple-ai@20fcbdebe0cdce3ac06e5ede639b8f78c177ceaa
  - src/cpp/evaluator.hpp
  - tests/test_evaluator_comprehensive.py
  - tests/test_joker.py

The final test deliberately models one source-level Joker-flush comparison rule
(`15` as a synthetic kicker above Ace) and demonstrates why that representation
must NOT be imported into the KKPoker row-local wildcard authority.
"""

from engine import (
    Card,
    CAT_FLUSH,
    CAT_FULL_HOUSE,
    CAT_PAIR,
    CAT_QUADS,
    CAT_STRAIGHT,
    CAT_STRAIGHT_FLUSH,
    CAT_TRIPS,
    CAT_TWO_PAIR,
    _candidate_row_resolutions,
    _eval_regular,
    parse_cards,
    royalty,
    ROW_BOTTOM,
    ROW_MIDDLE,
    ROW_TOP,
)

EXTERNAL_REPO = "ainaosyusi/ofc-pineapple-ai"
EXTERNAL_SHA = "20fcbdebe0cdce3ac06e5ede639b8f78c177ceaa"
EXTERNAL_EVALUATOR_BLOB_SHA = ""  # provenance is recorded in the audit doc/workflow manifest


def C(text: str) -> Card:
    return Card.parse(text)


def eval3(text: str):
    return _eval_regular(parse_cards(text))


def eval5(text: str):
    return _eval_regular(parse_cards(text))


def best_row_rank(text: str):
    candidates = _candidate_row_resolutions(parse_cards(text))
    assert candidates
    return candidates[0][0]


def test_external_ace_regression_vectors_match_target() -> None:
    # V1 postmortem class: Ace must be strongest rank in made hands and kickers.
    assert eval5("As Ah Kd Qc Js") > eval5("Ks Kh Ad Qc Js")
    assert eval5("As Ah Kd Qc Js") > eval5("2s 2h Kd Qc Js")
    assert eval3("As Ah Kd") > eval3("Ks Kh Ad") > eval3("Qs Qh Ad") > eval3("2s 2h Ad")
    assert eval5("As Kh Qd Tc 8s") > eval5("Ks Qh Jd Tc 8s")
    assert eval5("Ks Kh Ad 3c 2s") > eval5("Ks Kh Qd 3c 2s")
    assert eval5("As Ah Ad Kc Qs") > eval5("Ks Kh Kd Ac Qs") > eval5("2s 2h 2d Ac Ks")


def test_external_category_and_straight_boundary_vectors_match_target() -> None:
    hands = (
        eval5("As Kh Qd Tc 8s"),
        eval5("As Ah Kd Qc Js"),
        eval5("As Ah Kd Kc Qs"),
        eval5("As Ah Ad Kc Qs"),
        eval5("Ts Jh Qd Kc As"),
        eval5("As Ks Qs 9s 8s"),
        eval5("As Ah Ad Kc Ks"),
        eval5("As Ah Ad Ac Ks"),
        eval5("9s Ts Js Qs Ks"),
    )
    assert tuple(h.category for h in hands) == (
        0,
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

    wheel = eval5("As 2h 3d 4c 5s")
    six_high = eval5("2s 3h 4d 5c 6s")
    broadway = eval5("Ts Jh Qd Kc As")
    assert wheel.category == CAT_STRAIGHT and wheel.tie == (5,)
    assert six_high.category == CAT_STRAIGHT and six_high.tie == (6,)
    assert broadway.category == CAT_STRAIGHT and broadway.tie == (14,)
    assert wheel < six_high < broadway


def test_external_joker_vectors_match_target_wildcard_semantics() -> None:
    assert best_row_rank("As JK1 JK2").category == CAT_TRIPS
    assert best_row_rank("2s 3s 4s 5s JK1").category == CAT_STRAIGHT_FLUSH
    assert best_row_rank("2s 2h 3d 4c JK1").category == CAT_TRIPS
    assert best_row_rank("8s 8h 8d 9c JK1").category == CAT_QUADS
    royal = best_row_rank("As Ks Qs Ts JK1")
    assert royal.category == CAT_STRAIGHT_FLUSH and royal.royal and royal.tie == (14,)


def test_external_royalty_table_vectors_match_target() -> None:
    assert royalty(eval3("6s 6h Ad"), ROW_TOP) == 1
    assert royalty(eval3("As Ah Kd"), ROW_TOP) == 9
    assert royalty(eval3("2s 2h 2d"), ROW_TOP) == 10
    assert royalty(eval3("As Ah Ad"), ROW_TOP) == 22

    assert royalty(eval5("2s 2h 2d Kc Qs"), ROW_MIDDLE) == 2
    assert royalty(eval5("2s 3h 4d 5c 6s"), ROW_MIDDLE) == 4
    assert royalty(eval5("As Js 9s 6s 3s"), ROW_MIDDLE) == 8
    assert royalty(eval5("As Ah Ad Kc Ks"), ROW_MIDDLE) == 12
    assert royalty(eval5("As Ah Ad Ac Ks"), ROW_MIDDLE) == 20
    assert royalty(eval5("9s Ts Js Qs Ks"), ROW_MIDDLE) == 30
    assert royalty(eval5("Ts Js Qs Ks As"), ROW_MIDDLE) == 50

    assert royalty(eval5("2s 3h 4d 5c 6s"), ROW_BOTTOM) == 2
    assert royalty(eval5("As Js 9s 6s 3s"), ROW_BOTTOM) == 4
    assert royalty(eval5("As Ah Ad Kc Ks"), ROW_BOTTOM) == 6
    assert royalty(eval5("As Ah Ad Ac Ks"), ROW_BOTTOM) == 10
    assert royalty(eval5("9s Ts Js Qs Ks"), ROW_BOTTOM) == 15
    assert royalty(eval5("Ts Js Qs Ks As"), ROW_BOTTOM) == 25


def _external_source_flush_key_with_joker_above_ace(text: str) -> tuple[int, ...]:
    """Minimal reproduction of the audited source's non-SF flush kicker rule.

    `evaluator.hpp` inserts comparison rank 15 once per Joker before the natural
    suited ranks.  It is intentionally isolated here so a source-level semantic
    difference is executable evidence rather than prose only.
    """
    cards = parse_cards(text)
    jokers = sum(card.joker != 0 for card in cards)
    regular = [card for card in cards if not card.joker]
    assert jokers > 0
    assert len({card.suit for card in regular}) == 1
    ranks = sorted((card.rank for card in regular), reverse=True)
    return tuple([15] * jokers + ranks)[:5]


def _natural_flush_key(text: str) -> tuple[int, ...]:
    rank = eval5(text)
    assert rank.category == CAT_FLUSH
    return rank.tie


def test_reject_external_super_joker_flush_comparison_semantics() -> None:
    # Neither hand is a straight flush.  Under a real wildcard substitution,
    # JK in H1 should become Ks, yielding A-K-9-8-7.  H2 is A-K-Q-9-8 and is
    # therefore stronger.  The audited external source instead prepends a
    # synthetic rank 15, which reverses this comparison.
    h1 = "As 9s 8s 7s JK1"
    h2 = "As Ks Qs 9s 8s"

    target_h1 = best_row_rank(h1)
    target_h2 = _natural_flush_key(h2)
    assert target_h1.category == CAT_FLUSH
    assert target_h1.tie == (14, 13, 9, 8, 7)
    assert target_h2 == (14, 13, 12, 9, 8)
    assert target_h1.tie < target_h2

    external_h1 = _external_source_flush_key_with_joker_above_ace(h1)
    external_h2 = target_h2
    assert external_h1[0] == 15
    assert external_h1 > external_h2

    # Decision: this external comparison representation is incompatible with
    # the frozen target and must never be promoted into the evaluator authority.
