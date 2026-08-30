from __future__ import annotations

"""Isolated research solver using the exact 06S0 global-suit orbit.

This module deliberately does not modify strategic_cfr. It reuses the same
outcome-sampling update equations while replacing only the regret-table
information/action keys by their proven lossless suit-canonical equivalents.
"""

import gzip
import json
import math
from pathlib import Path

from external_06s0_suit_automorphism import canonical_information_state, permute_action_key
from strategic_cfr import (
    HUState,
    InfoSetNode,
    OutcomeSamplingMCCFR,
    _decode_rng_state,
    _sample_index,
    child_state,
    legal_action_pairs,
    terminal_utility,
)

SUIT_CANONICAL_CHECKPOINT_SCHEMA = "openofc-hu-os-mccfr-suit-orbit24-v1"
SUIT_CANONICALIZATION_ID = "GLOBAL_SUIT_ORBIT_LEXMIN_24_V1"


class SuitCanonicalOutcomeSamplingMCCFR(OutcomeSamplingMCCFR):
    """Outcome-sampling MCCFR sharing exact global-suit-isomorphic infosets."""

    def _canonical_pairs(self, state: HUState):
        key, perm = canonical_information_state(state)
        rows = [
            (permute_action_key(raw_key, perm), action)
            for raw_key, action in legal_action_pairs(state)
        ]
        rows.sort(key=lambda row: row[0])
        keys = [canonical_key for canonical_key, _action in rows]
        if len(keys) != len(set(keys)):
            raise AssertionError("suit orbit collapsed two legal actions inside one information state")
        return key, rows

    def _episode(
        self,
        state: HUState,
        update_player: int,
        *,
        my_reach: float,
        opp_reach: float,
        sample_reach: float,
    ) -> float:
        if state.terminal():
            return terminal_utility(state, update_player)

        current = state.actor
        key, canonical_pairs = self._canonical_pairs(state)
        action_keys = [canonical_key for canonical_key, _action in canonical_pairs]
        actions = [action for _canonical_key, action in canonical_pairs]
        node = self._node(key, action_keys)
        policy = node.current_policy()

        if current == update_player:
            uniform = 1.0 / len(policy)
            sample_policy = [
                self.epsilon * uniform + (1.0 - self.epsilon) * p
                for p in policy
            ]
        else:
            sample_policy = list(policy)

        sampled = _sample_index(sample_policy, self.rng)
        if current == update_player:
            new_my_reach = my_reach * policy[sampled]
            new_opp_reach = opp_reach
        else:
            new_my_reach = my_reach
            new_opp_reach = opp_reach * policy[sampled]
        new_sample_reach = sample_reach * sample_policy[sampled]
        child_value = self._episode(
            child_state(state, actions[sampled]),
            update_player,
            my_reach=new_my_reach,
            opp_reach=new_opp_reach,
            sample_reach=new_sample_reach,
        )

        child_values = [0.0] * len(policy)
        child_values[sampled] = child_value / sample_policy[sampled]
        value_estimate = sum(policy[i] * child_values[i] for i in range(len(policy)))

        if current == update_player:
            if sample_reach <= 0.0:
                raise AssertionError("sample reach became non-positive")
            scale = opp_reach / sample_reach
            cf_value = value_estimate * scale
            for i in range(len(policy)):
                delta = child_values[i] * scale - cf_value
                updated = node.cumulative_regrets[i] + delta
                node.cumulative_regrets[i] = max(0.0, updated) if self.cfr_plus else updated
            for i in range(len(policy)):
                node.cumulative_policy[i] += my_reach * policy[i] / sample_reach
            node.visits += 1

        return value_estimate

    def checkpoint_payload(self) -> dict:
        payload = super().checkpoint_payload()
        payload["schema"] = SUIT_CANONICAL_CHECKPOINT_SCHEMA
        payload["canonicalization"] = SUIT_CANONICALIZATION_ID
        return payload

    @classmethod
    def load_checkpoint(cls, path: Path) -> "SuitCanonicalOutcomeSamplingMCCFR":
        if path.suffix == ".gz":
            with gzip.open(path, "rb") as handle:
                payload = json.loads(handle.read().decode("utf-8"))
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != SUIT_CANONICAL_CHECKPOINT_SCHEMA:
            raise ValueError("unsupported suit-canonical checkpoint schema")
        if payload.get("canonicalization") != SUIT_CANONICALIZATION_ID:
            raise ValueError("suit-canonical checkpoint has a different canonicalization mode")
        solver = cls(
            epsilon=float(payload["epsilon"]),
            seed=int(payload["seed"]),
            cfr_plus=bool(payload["cfr_plus"]),
        )
        solver.iterations = int(payload["iterations"])
        solver.episodes = int(payload["episodes"])
        for row in payload["nodes"]:
            node = InfoSetNode(
                action_keys=tuple(row["action_keys"]),
                cumulative_regrets=[float(x) for x in row["cumulative_regrets"]],
                cumulative_policy=[float(x) for x in row["cumulative_policy"]],
                visits=int(row["visits"]),
            )
            if not (
                len(node.action_keys)
                == len(node.cumulative_regrets)
                == len(node.cumulative_policy)
            ):
                raise ValueError("corrupt suit-canonical checkpoint node")
            solver.nodes[str(row["key"])] = node
        if "rng_state" not in payload:
            raise ValueError("suit-canonical checkpoint is missing RNG state")
        solver.rng.setstate(_decode_rng_state(payload["rng_state"]))
        return solver


def canonical_solver_finite(solver: SuitCanonicalOutcomeSamplingMCCFR) -> bool:
    for node in solver.nodes.values():
        if any(not math.isfinite(value) for value in node.cumulative_regrets):
            return False
        if any(not math.isfinite(value) or value < 0.0 for value in node.cumulative_policy):
            return False
        for probabilities in (node.current_policy(), node.average_policy()):
            if any(not math.isfinite(p) or p < 0.0 for p in probabilities):
                return False
            if not math.isclose(sum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-12):
                return False
    return True
