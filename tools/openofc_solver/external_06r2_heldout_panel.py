from __future__ import annotations

"""Neutral held-out posterior panels for conditional EXT-06R2.

This module contains no winner selection and no strategic ranking.  It only
materializes deterministic posterior-compatible worlds that are disjoint from
candidate learner RNG streams by seed construction.
"""

from dataclasses import dataclass
import hashlib
import json
import random

from external_06r0_conditioned_solver import ConditionedFixtureSpec, plan_sha256
from external_06r1_belief_correct import BeliefSupport, sample_belief_root
from external_06s0_suit_automorphism import canonical_information_state, canonical_legal_action_keys
from strategic_cfr import HUState, information_state_key

AUTHORITY = "R3_HELDOUT_EMPIRICAL_GAME_RESEARCH_ONLY"


@dataclass(frozen=True)
class HeldoutPanel:
    fixture_name: str
    seed: int
    worlds: tuple[HUState, ...]
    plan_sha256s: tuple[str, ...]
    panel_sha256: str

    @property
    def size(self) -> int:
        return len(self.worlds)


def _panel_digest(fixture_name: str, seed: int, hashes: tuple[str, ...]) -> str:
    payload = {
        "fixture": fixture_name,
        "seed": int(seed),
        "plan_sha256s": list(hashes),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_unique_heldout_panel(
    root: HUState,
    spec: ConditionedFixtureSpec,
    support: BeliefSupport,
    *,
    seed: int,
    size: int = 256,
    max_attempt_multiplier: int = 100,
) -> HeldoutPanel:
    if size <= 0:
        raise ValueError("held-out panel size must be positive")
    if max_attempt_multiplier <= 0:
        raise ValueError("max_attempt_multiplier must be positive")
    if (root.round_index, root.actor) != (spec.round_index, spec.actor):
        raise ValueError("root does not match fixture spec")

    raw_key = information_state_key(root)
    canonical_key = canonical_information_state(root)[0]
    legal_keys = canonical_legal_action_keys(root)
    rng = random.Random(int(seed))

    worlds: list[HUState] = []
    hashes: list[str] = []
    seen: set[str] = set()
    attempts = 0
    max_attempts = size * max_attempt_multiplier

    while len(worlds) < size and attempts < max_attempts:
        attempts += 1
        world = sample_belief_root(root, spec, support, rng)
        if information_state_key(world) != raw_key:
            raise AssertionError("held-out world changed raw root information")
        if canonical_information_state(world)[0] != canonical_key:
            raise AssertionError("held-out world changed canonical root information")
        if canonical_legal_action_keys(world) != legal_keys:
            raise AssertionError("held-out world changed canonical root legal actions")
        digest = plan_sha256(world.plan)
        if digest in seen:
            continue
        seen.add(digest)
        hashes.append(digest)
        worlds.append(world)

    if len(worlds) != size:
        raise RuntimeError(
            f"unable to build {size} unique held-out worlds after {attempts} attempts"
        )

    ordered_hashes = tuple(hashes)
    return HeldoutPanel(
        fixture_name=spec.name,
        seed=int(seed),
        worlds=tuple(worlds),
        plan_sha256s=ordered_hashes,
        panel_sha256=_panel_digest(spec.name, int(seed), ordered_hashes),
    )


def panel_probe(panel: HeldoutPanel, root: HUState) -> dict:
    if panel.size <= 0:
        raise ValueError("panel is empty")
    raw_key = information_state_key(root)
    canonical_key = canonical_information_state(root)[0]
    legal_keys = canonical_legal_action_keys(root)
    exact = all(
        information_state_key(world) == raw_key
        and canonical_information_state(world)[0] == canonical_key
        and canonical_legal_action_keys(world) == legal_keys
        for world in panel.worlds
    )
    return {
        "fixture": panel.fixture_name,
        "seed": panel.seed,
        "size": panel.size,
        "unique_plan_count": len(set(panel.plan_sha256s)),
        "all_root_information_exact": exact,
        "panel_sha256": panel.panel_sha256,
    }
