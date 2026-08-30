from __future__ import annotations

import json
from pathlib import Path
import random
import tempfile

from strategic_cfr import (
    CHECKPOINT_SCHEMA,
    DealPlan,
    HUState,
    OutcomeSamplingMCCFR,
    child_state,
    information_state_key,
    legal_action_pairs,
    sample_deal_plan,
    terminal_utility,
)


def _swap_hidden_dealer_cards(plan: DealPlan) -> DealPlan:
    dealer_open = list(plan.opening[1])
    rounds = [[list(packets[0]), list(packets[1])] for packets in plan.rounds]
    dealer_open[0], rounds[0][1][0] = rounds[0][1][0], dealer_open[0]
    opening = (plan.opening[0], tuple(sorted(dealer_open)))
    rebuilt = tuple(
        (tuple(sorted(packets[0])), tuple(sorted(packets[1])))
        for packets in rounds
    )
    return DealPlan(opening=opening, rounds=rebuilt)  # type: ignore[arg-type]


def _canonical_payload(solver: OutcomeSamplingMCCFR) -> str:
    return json.dumps(
        solver.checkpoint_payload(),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def test_deal_and_opening_action_space() -> None:
    plan = sample_deal_plan(random.Random(7))
    assert len(plan.dealt_cards()) == 34
    assert len(set(plan.dealt_cards())) == 34
    assert len(legal_action_pairs(HUState(plan=plan))) == 232


def test_nondealer_information_key_hides_dealer_private_cards() -> None:
    plan = sample_deal_plan(random.Random(11))
    altered = _swap_hidden_dealer_cards(plan)
    assert altered.opening[1] != plan.opening[1]
    assert altered.rounds[0][1] != plan.rounds[0][1]
    original = HUState(plan=plan)
    changed = HUState(plan=altered)
    assert information_state_key(original) == information_state_key(changed)
    assert [key for key, _ in legal_action_pairs(original)] == [
        key for key, _ in legal_action_pairs(changed)
    ]


def test_public_history_exposes_placements_not_opponent_discard() -> None:
    plan = sample_deal_plan(random.Random(13))
    state = HUState(plan=plan)

    state = child_state(state, legal_action_pairs(state)[0][1])
    dealer_key = information_state_key(state)
    for card in plan.opening[0]:
        assert str(card) in dealer_key
    state = child_state(state, legal_action_pairs(state)[0][1])
    assert state.round_index == 1 and state.actor == 0

    incoming = plan.rounds[0][0]
    _key, action = legal_action_pairs(state)[0]
    assert action.discard_index is not None
    discarded = incoming[action.discard_index]
    state = child_state(state, action)
    assert discarded in state.discards[0]
    assert state.actor == 1
    dealer_key = information_state_key(state)
    assert str(discarded) not in dealer_key
    event = state.public_history[-1]
    assert all(card != str(discarded) for card, _row in event.placements)

    state = child_state(state, legal_action_pairs(state)[0][1])
    assert str(discarded) in information_state_key(state)


def test_complete_state_and_zero_sum_terminal_utility() -> None:
    plan = sample_deal_plan(random.Random(17))
    rng = random.Random(19)
    state = HUState(plan=plan)
    observed = []
    while not state.terminal():
        observed.append((state.round_index, state.actor))
        pairs = legal_action_pairs(state)
        state = child_state(state, pairs[rng.randrange(len(pairs))][1])
    assert observed == [
        (0, 0), (0, 1), (1, 0), (1, 1), (2, 0),
        (2, 1), (3, 0), (3, 1), (4, 0), (4, 1),
    ]
    u0 = terminal_utility(state, 0)
    u1 = terminal_utility(state, 1)
    assert u0 == -u1
    assert state.boards[0].count() == state.boards[1].count() == 13
    assert len(state.discards[0]) == len(state.discards[1]) == 4
    assert len(state.public_history) == 10


def test_outcome_sampling_smoke_and_checkpoint() -> None:
    solver = OutcomeSamplingMCCFR(seed=23, epsilon=0.6, cfr_plus=True)
    stats = solver.run(3)
    assert stats.iterations == 3 and stats.episodes == 6
    assert stats.infosets > 0 and stats.total_visits > 0
    assert stats.max_actions == 232
    assert solver.checkpoint_payload()["schema"] == CHECKPOINT_SCHEMA
    assert "rng_state" in solver.checkpoint_payload()
    for key, node in solver.nodes.items():
        policy = solver.policy_for_key(key)
        assert set(policy) == set(node.action_keys)
        assert abs(sum(policy.values()) - 1.0) < 1e-9
        assert all(p >= 0.0 for p in policy.values())
        assert all(x >= 0.0 for x in node.cumulative_regrets)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "solver.json.gz"
        solver.save_checkpoint(path)
        restored = OutcomeSamplingMCCFR.load_checkpoint(path)
        assert restored.iterations == solver.iterations
        assert restored.episodes == solver.episodes
        assert restored.nodes.keys() == solver.nodes.keys()
        assert restored.rng.getstate() == solver.rng.getstate()
        assert _canonical_payload(restored) == _canonical_payload(solver)


def test_checkpoint_resume_matches_uninterrupted_training_exactly() -> None:
    seed = 20260830
    first = 3
    second = 4

    uninterrupted = OutcomeSamplingMCCFR(seed=seed, epsilon=0.6, cfr_plus=True)
    uninterrupted.run(first + second)

    staged = OutcomeSamplingMCCFR(seed=seed, epsilon=0.6, cfr_plus=True)
    staged.run(first)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "resume.json.gz"
        staged.save_checkpoint(path)
        resumed = OutcomeSamplingMCCFR.load_checkpoint(path)
        resumed.run(second)

    assert _canonical_payload(resumed) == _canonical_payload(uninterrupted)


def test_cfr_modes_are_distinct_and_checkpointed() -> None:
    plus = OutcomeSamplingMCCFR(seed=31, epsilon=0.6, cfr_plus=True)
    vanilla = OutcomeSamplingMCCFR(seed=31, epsilon=0.6, cfr_plus=False)
    plus.run(8)
    vanilla.run(8)
    assert plus.cfr_plus is True and vanilla.cfr_plus is False
    assert all(x >= 0.0 for node in plus.nodes.values() for x in node.cumulative_regrets)
    assert any(x < 0.0 for node in vanilla.nodes.values() for x in node.cumulative_regrets)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "vanilla.json"
        vanilla.save_checkpoint(path)
        restored = OutcomeSamplingMCCFR.load_checkpoint(path)
        assert restored.cfr_plus is False
        assert restored.rng.getstate() == vanilla.rng.getstate()
        assert _canonical_payload(restored) == _canonical_payload(vanilla)


def test_same_seed_training_is_reproducible() -> None:
    a = OutcomeSamplingMCCFR(seed=41, epsilon=0.6, cfr_plus=True)
    b = OutcomeSamplingMCCFR(seed=41, epsilon=0.6, cfr_plus=True)
    a.run(5)
    b.run(5)
    assert _canonical_payload(a) == _canonical_payload(b)


def main() -> None:
    test_deal_and_opening_action_space()
    test_nondealer_information_key_hides_dealer_private_cards()
    test_public_history_exposes_placements_not_opponent_discard()
    test_complete_state_and_zero_sum_terminal_utility()
    test_outcome_sampling_smoke_and_checkpoint()
    test_checkpoint_resume_matches_uninterrupted_training_exactly()
    test_cfr_modes_are_distinct_and_checkpointed()
    test_same_seed_training_is_reproducible()
    print("OPENOFC_STRATEGIC_CFR_TEST=PASS")


if __name__ == "__main__":
    main()
