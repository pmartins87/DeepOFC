from __future__ import annotations

import pytest

from external_r4_infoset_search import exact_uniform_support_values
from external_r4_two_level_infoset_search import (
    AUTHORITY,
    run_uniform_support_two_level_uct,
)
from strategic_cfr import information_state_key
from test_external_r4_infoset_search import _coherent_r4_state, _support


def test_two_level_search_preserves_hidden_packet_blind_root() -> None:
    support = _support()
    state = _coherent_r4_state(support[0])
    result = run_uniform_support_two_level_uct(
        state,
        support,
        iterations=2_000,
        seed=2026082806,
        root_exploration=1.0,
        reply_exploration=1.0,
    )
    assert result.authority == AUTHORITY
    assert result.root_information_state_key == information_state_key(state)
    assert result.packet_count == len(support)
    assert sum(stat.visits for stat in result.root_action_stats) == result.iterations
    assert result.p1_infoset_count > 0
    assert 0 <= result.p1_fully_explored_infosets <= result.p1_infoset_count


def test_two_level_search_is_deterministic_and_recovers_exact_selected_value() -> None:
    support = _support()
    state = _coherent_r4_state(support[0])
    exact = exact_uniform_support_values(state, support)

    kwargs = dict(
        iterations=50_000,
        seed=2026082806,
        root_exploration=1.0,
        reply_exploration=1.0,
    )
    a = run_uniform_support_two_level_uct(state, support, **kwargs)
    b = run_uniform_support_two_level_uct(state, support, **kwargs)
    assert a == b
    assert a.selected_action_key in exact.best_action_keys
    assert a.selected_support_worlds_seen == len(support)
    assert a.selected_support_worlds_fully_explored == len(support)
    assert a.selected_support_backup_complete
    assert a.selected_support_backed_value is not None
    exact_by_key = dict(exact.action_values)
    assert abs(a.selected_support_backed_value - exact_by_key[a.selected_action_key]) <= 1e-12


def test_two_level_search_validation_fails_closed() -> None:
    support = _support()
    state = _coherent_r4_state(support[0])
    with pytest.raises(ValueError, match="iterations"):
        run_uniform_support_two_level_uct(state, support, iterations=0, seed=1)
    with pytest.raises(ValueError, match="root_exploration"):
        run_uniform_support_two_level_uct(
            state,
            support,
            iterations=10,
            seed=1,
            root_exploration=-0.1,
        )
    with pytest.raises(ValueError, match="reply_exploration"):
        run_uniform_support_two_level_uct(
            state,
            support,
            iterations=10,
            seed=1,
            reply_exploration=float("inf"),
        )
