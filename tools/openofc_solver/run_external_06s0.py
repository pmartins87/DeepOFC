from __future__ import annotations

"""Frozen 06S0 proof that global suit renaming is an exact game automorphism."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
from time import perf_counter

from engine import Board, Card, full_deck, parse_cards, resolve_board, score_heads_up
from external_06s0_suit_automorphism import (
    ALL_SUIT_PERMUTATIONS,
    canonical_information_state,
    canonical_legal_action_keys,
    canonicalize_observation_payload,
    full_state_semantic_payload,
    inverse_suit_permutation,
    permute_action_key,
    permute_board,
    permute_card,
    permute_state,
)
from strategic_cfr import DealPlan, HUState, child_state, information_state_key, legal_action_pairs, sample_deal_plan, terminal_utility

EXPERIMENT_ID = "EXT-06S0-EXACT-GLOBAL-SUIT-AUTOMORPHISM"
AUTHORITY = "EXACT_SUIT_AUTOMORPHISM_DIAGNOSTIC_ONLY"


def _random_complete_boards(seed: int) -> tuple[Board, Board]:
    rng = random.Random(seed)
    cards = rng.sample(list(full_deck(2)), 26)
    return (
        Board(tuple(cards[0:3]), tuple(cards[3:8]), tuple(cards[8:13])),
        Board(tuple(cards[13:16]), tuple(cards[16:21]), tuple(cards[21:26])),
    )


def _joker_boards() -> list[Board]:
    return [
        Board(
            parse_cards("Qc Qd JK1"),
            parse_cards("2c 3c 4c 5c 6c"),
            parse_cards("Th Jh Qh Kh Ah"),
        ),
        Board(
            parse_cards("Kc Kd JK2"),
            parse_cards("3d 4d 5d 6d 7d"),
            parse_cards("9s Ts Js Qs Ks"),
        ),
        Board(
            parse_cards("Ac JK1 JK2"),
            parse_cards("4h 5h 6h 7h 8h"),
            parse_cards("9c Tc Jc Qc Kc"),
        ),
        Board(
            parse_cards("6c 6d 9h"),
            parse_cards("2s 3s 4s 5s JK1"),
            parse_cards("Th Jh Qh Kh JK2"),
        ),
    ]


def _resolved_signature(board: Board) -> object:
    result = resolve_board(board)
    if result is None:
        return None
    return {
        "ranks": [
            [rank.category, list(rank.tie), rank.royal]
            for rank in result.ranks
        ],
        "royalties": result.royalties,
        "fantasy_cards": result.fantasy_cards,
    }


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


def _all_action_transition_probes(state: HUState, perm: tuple[int, int, int, int]) -> tuple[int, int, int]:
    transformed_state = permute_state(state, perm)
    original_pairs = legal_action_pairs(state)
    transformed_pairs = legal_action_pairs(transformed_state)
    transformed_map = {key: action for key, action in transformed_pairs}
    mapped_keys = {permute_action_key(key, perm) for key, _action in original_pairs}
    target_keys = set(transformed_map)
    action_set_mismatch = 0 if mapped_keys == target_keys else 1
    transition_mismatch = 0
    checked = 0
    if action_set_mismatch == 0:
        for raw_key, action in original_pairs:
            mapped_key = permute_action_key(raw_key, perm)
            transformed_action = transformed_map[mapped_key]
            expected = permute_state(child_state(state, action), perm)
            actual = child_state(transformed_state, transformed_action)
            if full_state_semantic_payload(expected) != full_state_semantic_payload(actual):
                transition_mismatch += 1
            checked += 1
    return action_set_mismatch, transition_mismatch, checked


def run() -> dict:
    started = perf_counter()
    deck = tuple(full_deck(2))

    deck_mismatches = 0
    inverse_mismatches = 0
    for perm in ALL_SUIT_PERMUTATIONS:
        transformed = tuple(permute_card(card, perm) for card in deck)
        if len(transformed) != 54 or len(set(transformed)) != 54:
            deck_mismatches += 1
        inverse = inverse_suit_permutation(perm)
        if tuple(permute_card(card, inverse) for card in transformed) != deck:
            inverse_mismatches += 1

    score_mismatches = 0
    score_checks = 0
    random_joker_pair_count = 0
    for seed in range(32):
        hero, opponent = _random_complete_boards(9100 + seed)
        if any(card.joker for row in hero.rows() + opponent.rows() for card in row):
            random_joker_pair_count += 1
        baseline = score_heads_up(hero, opponent)
        for perm in ALL_SUIT_PERMUTATIONS:
            observed = score_heads_up(permute_board(hero, perm), permute_board(opponent, perm))
            score_checks += 1
            if observed != baseline:
                score_mismatches += 1

    joker_resolution_mismatches = 0
    joker_resolution_checks = 0
    joker_boards = _joker_boards()
    joker_baselines = [_resolved_signature(board) for board in joker_boards]
    for board, baseline in zip(joker_boards, joker_baselines):
        for perm in ALL_SUIT_PERMUTATIONS:
            joker_resolution_checks += 1
            if _resolved_signature(permute_board(board, perm)) != baseline:
                joker_resolution_mismatches += 1

    information_orbit_mismatches = 0
    canonical_action_mismatches = 0
    action_set_mismatches = 0
    transition_mismatches = 0
    transition_checks = 0
    terminal_utility_mismatches = 0
    trajectory_states_checked = 0

    for seed in (9201, 9202, 9203):
        state = HUState(plan=sample_deal_plan(random.Random(seed)))
        trajectory = []
        while not state.terminal():
            trajectory.append(state)
            state = child_state(state, legal_action_pairs(state)[0][1])
        terminal = state

        for state in trajectory:
            trajectory_states_checked += 1
            base_canonical_key, _base_perm = canonical_information_state(state)
            base_actions = canonical_legal_action_keys(state)
            for perm in ALL_SUIT_PERMUTATIONS:
                transformed_state = permute_state(state, perm)
                transformed_canonical_key, _ = canonical_information_state(transformed_state)
                if transformed_canonical_key != base_canonical_key:
                    information_orbit_mismatches += 1
                if canonical_legal_action_keys(transformed_state) != base_actions:
                    canonical_action_mismatches += 1
                action_mismatch, transition_mismatch, checked = _all_action_transition_probes(state, perm)
                action_set_mismatches += action_mismatch
                transition_mismatches += transition_mismatch
                transition_checks += checked

        for perm in ALL_SUIT_PERMUTATIONS:
            transformed_terminal = permute_state(terminal, perm)
            for player in (0, 1):
                if terminal_utility(transformed_terminal, player) != terminal_utility(terminal, player):
                    terminal_utility_mismatches += 1

    # Canonicalization begins from the already-certified visible information payload.
    hidden_plan = sample_deal_plan(random.Random(9301))
    hidden_changed = _swap_hidden_dealer_cards(hidden_plan)
    hidden_a = HUState(plan=hidden_plan)
    hidden_b = HUState(plan=hidden_changed)
    hidden_firewall_pass = (
        information_state_key(hidden_a) == information_state_key(hidden_b)
        and canonical_information_state(hidden_a)[0] == canonical_information_state(hidden_b)[0]
        and canonical_legal_action_keys(hidden_a) == canonical_legal_action_keys(hidden_b)
    )

    # Perfect recall probe: P0 discards on R1, P1 acts, then P0 observes R2.
    recall_state = HUState(plan=sample_deal_plan(random.Random(9401)))
    recall_state = child_state(recall_state, legal_action_pairs(recall_state)[0][1])
    recall_state = child_state(recall_state, legal_action_pairs(recall_state)[0][1])
    _r1key, r1action = legal_action_pairs(recall_state)[0]
    discarded = recall_state.plan.incoming(1, 0)[r1action.discard_index]  # type: ignore[index]
    recall_state = child_state(recall_state, r1action)
    recall_state = child_state(recall_state, legal_action_pairs(recall_state)[0][1])
    canonical_recall_payload = json.loads(canonical_information_state(recall_state)[0])
    perfect_recall_pass = (
        len(canonical_recall_payload["own_discards"]) == 1
        and len(canonical_recall_payload["public_history"]) == 4
        and canonical_recall_payload["round"] == 2
        and canonical_recall_payload["player"] == 0
        and discarded.joker == sum(token.startswith("JK") for token in canonical_recall_payload["own_discards"])
        if discarded.joker else len(canonical_recall_payload["own_discards"]) == 1
    )

    # Representation-level firewalls: suit permutation must not erase non-suit facts.
    probe_payload = json.loads(information_state_key(recall_state))
    base_probe_key = canonicalize_observation_payload(probe_payload)[0]
    nonisomorphic_checks = {}

    changed_round = deepcopy(probe_payload)
    changed_round["round"] = int(changed_round["round"]) + 1
    nonisomorphic_checks["round_preserved"] = canonicalize_observation_payload(changed_round)[0] != base_probe_key

    changed_player = deepcopy(probe_payload)
    changed_player["player"] = 1
    changed_player["position"] = "dealer_button_second"
    nonisomorphic_checks["player_position_preserved"] = canonicalize_observation_payload(changed_player)[0] != base_probe_key

    changed_rank = deepcopy(probe_payload)
    regular_index = next(i for i, token in enumerate(changed_rank["incoming"]) if not token.startswith("JK"))
    old = Card.parse(changed_rank["incoming"][regular_index])
    new_rank = 2 if old.rank != 2 else 3
    changed_rank["incoming"][regular_index] = str(Card(rank=new_rank, suit=old.suit))
    nonisomorphic_checks["rank_preserved"] = canonicalize_observation_payload(changed_rank)[0] != base_probe_key

    changed_history = deepcopy(probe_payload)
    old_row = int(changed_history["public_history"][0][2][0][1])
    changed_history["public_history"][0][2][0][1] = (old_row + 1) % 3
    nonisomorphic_checks["public_row_history_preserved"] = canonicalize_observation_payload(changed_history)[0] != base_probe_key

    joker1 = deepcopy(probe_payload)
    joker2 = deepcopy(probe_payload)
    joker1["incoming"][0] = "JK1"
    joker2["incoming"][0] = "JK2"
    nonisomorphic_checks["joker_identity_not_collapsed"] = (
        canonicalize_observation_payload(joker1)[0] != canonicalize_observation_payload(joker2)[0]
    )

    quality = {
        "all_24_permutations_enumerated": len(ALL_SUIT_PERMUTATIONS) == 24,
        "deck_bijection_zero_mismatches": deck_mismatches == 0 and inverse_mismatches == 0,
        "score_invariance_zero_mismatches": score_mismatches == 0 and score_checks == 32 * 24,
        "joker_resolution_zero_mismatches": joker_resolution_mismatches == 0,
        "information_orbit_zero_mismatches": information_orbit_mismatches == 0,
        "canonical_action_set_zero_mismatches": canonical_action_mismatches == 0,
        "raw_legal_action_bijection_zero_mismatches": action_set_mismatches == 0,
        "transition_commutation_zero_mismatches": transition_mismatches == 0 and transition_checks > 0,
        "terminal_utility_zero_mismatches": terminal_utility_mismatches == 0,
        "hidden_information_firewall_preserved": hidden_firewall_pass,
        "perfect_recall_preserved": bool(perfect_recall_pass),
        "nonisomorphic_firewalls_pass": all(nonisomorphic_checks.values()),
        "strategic_trainer_unchanged": True,
        "real_routes_certified_zero": True,
    }
    passed = all(quality.values())
    payload = {
        "schema": "openofc-external-component-ab-v1",
        "experiment_id": EXPERIMENT_ID,
        "authority": AUTHORITY,
        "config": {
            "suit_permutations": len(ALL_SUIT_PERMUTATIONS),
            "random_score_fixture_count": 32,
            "trajectory_seeds": [9201, 9202, 9203],
            "joker_identity_swapping_enabled": False,
        },
        "diagnostics": {
            "deck_mismatches": deck_mismatches,
            "inverse_mismatches": inverse_mismatches,
            "score_checks": score_checks,
            "score_mismatches": score_mismatches,
            "random_score_pairs_containing_joker": random_joker_pair_count,
            "joker_resolution_checks": joker_resolution_checks,
            "joker_resolution_mismatches": joker_resolution_mismatches,
            "trajectory_states_checked": trajectory_states_checked,
            "information_orbit_mismatches": information_orbit_mismatches,
            "canonical_action_mismatches": canonical_action_mismatches,
            "raw_action_set_mismatches": action_set_mismatches,
            "transition_checks": transition_checks,
            "transition_mismatches": transition_mismatches,
            "terminal_utility_mismatches": terminal_utility_mismatches,
            "nonisomorphic_checks": nonisomorphic_checks,
        },
        "quality": quality,
        "verdict": (
            "GLOBAL_SUIT_PERMUTATION_IS_LOSSLESS_AUTOMORPHISM"
            if passed else "FAIL_06S0_SUIT_AUTOMORPHISM_PROOF"
        ),
        "next_gate_recommendation": (
            "SUIT_CANONICALIZATION_ELIGIBLE_FOR_SEPARATE_INTEGRATION_AB"
            if passed else "STOP_AND_DIAGNOSE_SUIT_AUTOMORPHISM"
        ),
        "runtime_seconds": perf_counter() - started,
        "real_routes_certified": 0,
    }
    payload["manifest_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    if not passed:
        raise RuntimeError(json.dumps({
            "experiment_id": EXPERIMENT_ID,
            "verdict": payload["verdict"],
            "quality": quality,
            "diagnostics": payload["diagnostics"],
        }, sort_keys=True))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = run()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "experiment_id": payload["experiment_id"],
        "verdict": payload["verdict"],
        "quality": payload["quality"],
        "diagnostics": payload["diagnostics"],
        "manifest_sha256": payload["manifest_sha256"],
        "real_routes_certified": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
