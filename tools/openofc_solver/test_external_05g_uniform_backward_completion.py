from __future__ import annotations

from engine import Board, parse_cards
from external_05g_uniform_backward_completion import (
    SOURCE_LABEL,
    build_uniform_local_backward_completion,
    completion_policy_sha256,
)
from external_hidden_discard_overlap import OverlapWorld
from external_hidden_discard_overlap_strategic import build_reachable_support
from strategic_cfr import DealPlan, HUState, child_state, legal_action_pairs, terminal_utility


def B(top: str, middle: str, bottom: str) -> Board:
    return Board(parse_cards(top), parse_cards(middle), parse_cards(bottom))


def four_world_fixture() -> tuple[HUState, tuple[OverlapWorld, ...]]:
    p0_types = (
        parse_cards("7c 8c 8h"),
        parse_cards("7c 8c 9d"),
    )
    p1_types = (
        parse_cards("Ah Kh Qh"),
        parse_cards("Ah Kh Ks"),
    )
    p0_r4 = parse_cards("9h Th Td")
    p1_r4 = parse_cards("Ad Kc Qs")
    worlds = tuple(
        OverlapWorld(
            world_id=f"p0t{i}-p1t{j}",
            p0_r3=p0,
            p1_r3=p1,
            p0_r4=p0_r4,
            p1_r4=p1_r4,
        )
        for i, p0 in enumerate(p0_types)
        for j, p1 in enumerate(p1_types)
    )
    w = worlds[0]
    plan = DealPlan(
        opening=(
            parse_cards("Qc 2c 3c 4c 5c"),
            parse_cards("Jc 4h 5h 9c Tc"),
        ),
        rounds=(
            (parse_cards("Qd 2d 2h"), parse_cards("Jd 6h 2s")),
            (parse_cards("3d 6c 3h"), parse_cards("7h Jh 3s")),
            (w.p0_r3, w.p1_r3),
            (w.p0_r4, w.p1_r4),
        ),
    )
    base = HUState(
        plan=plan,
        round_index=3,
        actor=0,
        boards=(
            B("Qc Qd", "2c 2d 3c 3d", "4c 5c 6c"),
            B("Jc Jd", "4h 5h 6h 7h", "9c Tc Jh"),
        ),
        discards=(parse_cards("2h 3h"), parse_cards("2s 3s")),
        public_history=(),
    )
    return base, worlds


def test_uniform_backward_completion_is_complete_legal_pure_and_deterministic() -> None:
    base, worlds = four_world_fixture()
    support = build_reachable_support(base, worlds)
    first = build_uniform_local_backward_completion(support)
    second = build_uniform_local_backward_completion(support)

    assert first.source_label == SOURCE_LABEL
    assert first.information_states == len(support)
    assert first.selected_actions == second.selected_actions
    assert first.policy_sha256 == second.policy_sha256
    assert first.policy_sha256 == completion_policy_sha256(first.choice_map())

    choices = first.choice_map()
    for row in support:
        assert choices[row.information_state_key] in row.action_keys


def test_last_actor_r4_completion_is_exact_local_minimum_u0() -> None:
    base, worlds = four_world_fixture()
    support = build_reachable_support(base, worlds)
    completion = build_uniform_local_backward_completion(support)
    choices = completion.choice_map()

    checked = 0
    for row in support:
        if (row.round_index, row.actor) != (4, 1):
            continue
        means = {}
        for action_key in row.action_keys:
            total = 0.0
            for state in row.concrete_states:
                action = dict(legal_action_pairs(state))[action_key]
                terminal = child_state(state, action)
                assert terminal.terminal()
                total += float(terminal_utility(terminal, 0))
            means[action_key] = total / len(row.concrete_states)
        selected = choices[row.information_state_key]
        assert means[selected] == min(means.values())
        checked += 1
        if checked >= 25:
            break
    assert checked == 25
