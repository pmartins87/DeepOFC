from __future__ import annotations

import pytest

from engine import Board, Card, parse_cards
from external_r4_infoset_search import (
    AUTHORITY,
    exact_uniform_support_values,
    run_uniform_support_root_uct,
)
from strategic_cfr import DealPlan, HUState, information_state_key


def C(text: str) -> Card:
    return Card.parse(text)


def B(top: str, middle: str, bottom: str) -> Board:
    return Board(parse_cards(top), parse_cards(middle), parse_cards(bottom))


def _coherent_r4_state(placeholder_p1_packet: tuple[Card, ...]) -> HUState:
    # Every pre-R4 card in the plan corresponds to one visible placement or one
    # private discard in this fixture.  The only alternate hidden variable used
    # by the experiment is P1's current R4 packet.
    plan = DealPlan(
        opening=(
            parse_cards("Qc 2c 3c 4c 5c"),
            parse_cards("Jc 4h 5h 9c Tc"),
        ),
        rounds=(
            (parse_cards("Qd 2d 2h"), parse_cards("Jd 6h 2s")),
            (parse_cards("3d 6c 3h"), parse_cards("7h Jh 3s")),
            (parse_cards("7c 8c 8h"), parse_cards("Qs Kd 8s")),
            (parse_cards("Qh 9d As"), tuple(placeholder_p1_packet)),
        ),
    )
    return HUState(
        plan=plan,
        round_index=4,
        actor=0,
        boards=(
            B("Qc Qd", "2c 2d 3c 3d", "4c 5c 6c 7c 8c"),
            B("Jc Jd", "4h 5h 6h 7h", "9c Tc Jh Qs Kd"),
        ),
        discards=(parse_cards("2h 3h 8h"), parse_cards("2s 3s 8s")),
        public_history=(),
    )


def _support() -> tuple[tuple[Card, ...], ...]:
    return tuple(
        parse_cards(packet)
        for packet in (
            "Ah Ks Kc",
            "Ah Kh Td",
            "Ks Js 9h",
            "Kc Th 8d",
            "Kh Td 7d",
            "Js 9s 6d",
            "Th 8d 5d",
            "Td 7d 4d",
            "9h 6d 5s",
            "JK1 Ks 5d",
            "JK2 Th 4d",
            "Ah JK1 JK2",
        )
    )


def test_exact_support_keeps_one_root_infoset_and_returns_finite_values() -> None:
    support = _support()
    state = _coherent_r4_state(support[0])
    result = exact_uniform_support_values(state, support)
    assert result.packet_count == len(support)
    assert result.root_information_state_key == information_state_key(state)
    assert result.action_values
    assert result.best_action_keys
    assert result.best_value == max(value for _key, value in result.action_values)


def test_root_uct_is_deterministic_and_converges_to_exact_support_optimum() -> None:
    support = _support()
    state = _coherent_r4_state(support[0])
    exact = exact_uniform_support_values(state, support)

    a = run_uniform_support_root_uct(
        state,
        support,
        iterations=50_000,
        seed=2026082805,
        exploration=1.0,
    )
    b = run_uniform_support_root_uct(
        state,
        support,
        iterations=50_000,
        seed=2026082805,
        exploration=1.0,
    )
    assert a == b
    assert a.authority == AUTHORITY
    assert a.root_information_state_key == exact.root_information_state_key
    assert a.selected_action_key in exact.best_action_keys
    assert sum(stat.visits for stat in a.action_stats) == a.iterations
    assert a.determinized_reply_cache_entries <= len(support) * len(a.action_stats)

    by_key = dict(exact.action_values)
    selected_stat = next(stat for stat in a.action_stats if stat.action_key == a.selected_action_key)
    # The selected arm should estimate the exact finite-support expectation to a
    # useful screening tolerance after 50k root iterations.
    assert abs(selected_stat.mean_value - by_key[a.selected_action_key]) <= 0.20


def test_support_validation_fails_closed() -> None:
    state = _coherent_r4_state(parse_cards("Ah Ks Kc"))
    with pytest.raises(ValueError, match="at least two"):
        exact_uniform_support_values(state, (parse_cards("Ah Ks Kc"),))
    with pytest.raises(ValueError, match="exactly three"):
        exact_uniform_support_values(
            state,
            (parse_cards("Ah Ks Kc"), parse_cards("Kh Td")),
        )
    with pytest.raises(ValueError, match="duplicate worlds"):
        exact_uniform_support_values(
            state,
            (parse_cards("Ah Ks Kc"), parse_cards("Kc Ah Ks")),
        )
