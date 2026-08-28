from __future__ import annotations

"""Authority firewall for external late exact/bounded-search ideas.

A search can be exact *inside one fully specified hidden world* while still not
be an exact imperfect-information policy.  This test freezes that distinction
for HU Pineapple final-round states.
"""

from itertools import combinations

from engine import Board, Card, parse_cards
from strategic_cfr import (
    DealPlan,
    HUState,
    child_state,
    information_state_key,
    legal_action_pairs,
    terminal_utility,
)


def C(text: str) -> Card:
    return Card.parse(text)


def B(top: str, middle: str, bottom: str) -> Board:
    return Board(parse_cards(top), parse_cards(middle), parse_cards(bottom))


def _plan(p0_r4: tuple[Card, ...], p1_r4: tuple[Card, ...]) -> DealPlan:
    # Earlier packets are irrelevant to the R4 authority test.  They are kept
    # stable so the two worlds differ only in the hidden opponent R4 packet.
    return DealPlan(
        opening=(
            parse_cards("Ac Kc Qs Js Ts"),
            parse_cards("Ad Kh Qh Jd Td"),
        ),
        rounds=(
            (parse_cards("2h 3h 8h"), parse_cards("2s 3s 8s")),
            (parse_cards("5s 6s 7s"), parse_cards("5d 6d 7d")),
            (parse_cards("9h Th Jh"), parse_cards("9s Tc Jc")),
            (p0_r4, p1_r4),
        ),
    )


def _root_state(p1_r4: tuple[Card, ...]) -> HUState:
    p0_board = B(
        "Qc Qd",
        "2c 2d 3c 3d",
        "4c 5c 6c 7c 8c",
    )
    p1_board = B(
        "Jc Jd",
        "4h 5h 6h 7h",
        "9c Tc Jh Qs Kd",
    )
    p0_r4 = parse_cards("Qh 9d As")
    return HUState(
        plan=_plan(p0_r4, p1_r4),
        round_index=4,
        actor=0,
        boards=(p0_board, p1_board),
        discards=(parse_cards("2h 3h 8h"), parse_cards("2s 3s 8s")),
        public_history=(),
    )


def _perfect_information_r4_best_keys(state: HUState) -> tuple[str, ...]:
    """Solve the last round after illegally revealing both private packets.

    This is a useful reference inside a determinization, but its root action is
    not a legal exact infoset policy when the opponent packet is still hidden.
    """
    root_values: list[tuple[str, float]] = []
    for root_key, root_action in legal_action_pairs(state):
        after_root = child_state(state, root_action)
        replies = legal_action_pairs(after_root)
        assert replies
        reply_values = []
        for _reply_key, reply_action in replies:
            terminal = child_state(after_root, reply_action)
            assert terminal.terminal()
            reply_values.append(terminal_utility(terminal, 0))
        root_values.append((root_key, min(reply_values)))
    best = max(value for _key, value in root_values)
    return tuple(sorted(key for key, value in root_values if value == best))


def test_same_infoset_can_contain_hidden_worlds_with_different_perfect_info_actions() -> None:
    # Candidate unseen cards intentionally exclude all board cards, P0's packet,
    # and the synthetic prior discards used by this final-round fixture.
    occupied = set(
        parse_cards(
            "Qc Qd 2c 2d 3c 3d 4c 5c 6c 7c 8c "
            "Jc Jd 4h 5h 6h 7h 9c Tc Jh Qs Kd "
            "Qh 9d As 2h 3h 8h 2s 3s 8s"
        )
    )
    pool = tuple(
        card
        for card in (
            C("Ah"), C("Ks"), C("Kc"), C("Kh"), C("Qd"), C("Qh"),
            C("Js"), C("Th"), C("Td"), C("9h"), C("9s"), C("8d"),
            C("7d"), C("6d"), C("5d"), C("4d"), C("3h"), C("2d"),
            C("JK1"), C("JK2"),
        )
        if card not in occupied
    )

    reference_key = None
    observed_best_sets: dict[tuple[str, ...], tuple[Card, ...]] = {}
    for packet in combinations(pool, 3):
        state = _root_state(tuple(packet))
        key = information_state_key(state)
        if reference_key is None:
            reference_key = key
        else:
            # Opponent current packet must not change P0's legal information set.
            assert key == reference_key

        best_keys = _perfect_information_r4_best_keys(state)
        observed_best_sets.setdefault(best_keys, tuple(packet))
        if len(observed_best_sets) >= 2:
            break

    # At least two hidden worlds inside the exact same P0 information set cause
    # a full-information final-round solver to prefer different P0 actions.
    # Therefore determinize->minimax cannot be labeled an exact infoset policy.
    assert len(observed_best_sets) >= 2


def test_fully_observed_terminal_teacher_remains_valid_reference() -> None:
    # Once both packets/actions have actually been revealed and the state is
    # terminal, exact utility is unambiguous and zero-sum.  The authority problem
    # is specifically the use of hidden-world knowledge *before* revelation.
    state = _root_state((C("Ah"), C("Ks"), C("Td")))
    root_key, root_action = legal_action_pairs(state)[0]
    assert root_key
    after_root = child_state(state, root_action)
    _reply_key, reply_action = legal_action_pairs(after_root)[0]
    terminal = child_state(after_root, reply_action)
    assert terminal.terminal()
    u0 = terminal_utility(terminal, 0)
    u1 = terminal_utility(terminal, 1)
    assert u0 == -u1
