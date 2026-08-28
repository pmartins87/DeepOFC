from __future__ import annotations

"""Exact conditional reach audit for ambiguous 05F information sets.

Authority:
  HIDDEN_DISCARD_OVERLAP_CONDITIONAL_REACH_AUDIT_ONLY
"""

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from external_hidden_discard_overlap import OverlapWorld, validate_worlds, with_overlap_world
from external_hidden_discard_overlap_strategic import ReachableSupport
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs

AUTHORITY = "HIDDEN_DISCARD_OVERLAP_CONDITIONAL_REACH_AUDIT_ONLY"
SCHEMA = "openofc-external-hidden-discard-overlap-reach-audit-v1"
ReadOnlyProfile = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class ReachAuditRow:
    information_state_key: str
    round_index: int
    actor: int
    compatible_states: int
    positive_full_states: int
    positive_counterfactual_states: int
    uniform_vs_full_tv: float | None
    uniform_vs_counterfactual_tv: float | None
    full_vs_counterfactual_tv: float | None
    full_effective_support: float | None
    counterfactual_effective_support: float | None


@dataclass(frozen=True)
class ReachAudit:
    authority: str
    support_worlds: int
    information_states: int
    ambiguous_information_states: int
    rows: tuple[ReachAuditRow, ...]


def _distribution(profile: ReadOnlyProfile, key: str, action_keys: Sequence[str]) -> dict[str, float]:
    supplied = profile.get(key)
    if supplied is None:
        raise ValueError(f"reach audit requires explicit policy at infoset: {key}")
    illegal = set(supplied) - set(action_keys)
    if illegal:
        raise ValueError(f"profile contains illegal actions: {sorted(illegal)}")
    weights = {}
    for action_key in action_keys:
        value = float(supplied.get(action_key, 0.0))
        if value < 0.0 or not math.isfinite(value):
            raise ValueError("profile probabilities must be finite and non-negative")
        weights[action_key] = value
    mass = sum(weights.values())
    if mass <= 0.0:
        raise ValueError("reach audit refuses zero-mass policy")
    return {key: value / mass for key, value in weights.items()}


def _normalize(raw: Mapping[str, float]) -> dict[str, float] | None:
    positive = {key: float(value) for key, value in raw.items() if value > 0.0}
    mass = sum(positive.values())
    if mass <= 0.0:
        return None
    return {key: value / mass for key, value in positive.items()}


def _tv(p: Mapping[str, float], q: Mapping[str, float]) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(float(p.get(key, 0.0)) - float(q.get(key, 0.0))) for key in keys)


def _effective_support(p: Mapping[str, float] | None) -> float | None:
    if p is None:
        return None
    denom = sum(value * value for value in p.values())
    return 1.0 / denom if denom > 0.0 else None


def audit_overlap_conditional_reach(
    base_state: HUState,
    worlds: Sequence[OverlapWorld],
    *,
    support_rows: Sequence[ReachableSupport],
    profile: ReadOnlyProfile,
) -> ReachAudit:
    support = validate_worlds(worlds)
    if not support_rows:
        raise ValueError("reach audit requires reachable support rows")
    expected = {row.information_state_key for row in support_rows}
    missing = expected - set(profile)
    if missing:
        raise ValueError(f"reach audit profile incomplete: missing={len(missing)}")

    row_by_key = {row.information_state_key: row for row in support_rows}
    # key -> concrete-state repr -> [full reach, acting-player CF reach]
    accum: dict[str, dict[str, list[float]]] = {key: {} for key in expected}
    chance = 1.0 / len(support)

    def walk(state: HUState, reach0: float, reach1: float) -> None:
        if state.terminal():
            return
        key = information_state_key(state)
        row = row_by_key.get(key)
        if row is None:
            raise AssertionError("profile traversal reached an infoset outside exact support")
        fingerprint = repr(state)
        full = chance * reach0 * reach1
        cf = chance * (reach1 if state.actor == 0 else reach0)
        bucket = accum[key].setdefault(fingerprint, [0.0, 0.0])
        bucket[0] += full
        bucket[1] += cf

        pairs = tuple(legal_action_pairs(state))
        action_keys = tuple(action_key for action_key, _action in pairs)
        dist = _distribution(profile, key, action_keys)
        by_key = dict(pairs)
        # Do not prune zero-probability own-strategy branches. A branch with zero
        # full reach can still have positive counterfactual reach at a later
        # information state of that same player.
        for action_key in action_keys:
            probability = dist[action_key]
            if state.actor == 0:
                walk(child_state(state, by_key[action_key]), reach0 * probability, reach1)
            else:
                walk(child_state(state, by_key[action_key]), reach0, reach1 * probability)

    for world in support:
        walk(with_overlap_world(base_state, world), 1.0, 1.0)

    rows_out = []
    for row in support_rows:
        key = row.information_state_key
        concrete_fingerprints = tuple(sorted(repr(state) for state in row.concrete_states))
        if len(set(concrete_fingerprints)) != len(concrete_fingerprints):
            raise AssertionError("support row contains duplicate concrete states")
        values = accum[key]
        full_raw = {fingerprint: values.get(fingerprint, [0.0, 0.0])[0] for fingerprint in concrete_fingerprints}
        cf_raw = {fingerprint: values.get(fingerprint, [0.0, 0.0])[1] for fingerprint in concrete_fingerprints}
        full = _normalize(full_raw)
        cf = _normalize(cf_raw)
        uniform = {fingerprint: 1.0 / len(concrete_fingerprints) for fingerprint in concrete_fingerprints}
        rows_out.append(
            ReachAuditRow(
                information_state_key=key,
                round_index=row.round_index,
                actor=row.actor,
                compatible_states=len(concrete_fingerprints),
                positive_full_states=sum(1 for value in full_raw.values() if value > 0.0),
                positive_counterfactual_states=sum(1 for value in cf_raw.values() if value > 0.0),
                uniform_vs_full_tv=None if full is None else _tv(uniform, full),
                uniform_vs_counterfactual_tv=None if cf is None else _tv(uniform, cf),
                full_vs_counterfactual_tv=None if full is None or cf is None else _tv(full, cf),
                full_effective_support=_effective_support(full),
                counterfactual_effective_support=_effective_support(cf),
            )
        )

    return ReachAudit(
        authority=AUTHORITY,
        support_worlds=len(support),
        information_states=len(rows_out),
        ambiguous_information_states=sum(1 for row in rows_out if row.compatible_states > 1),
        rows=tuple(rows_out),
    )


def summarize_overlap_reach(audit: ReachAudit) -> dict:
    ambiguous = [row for row in audit.rows if row.compatible_states > 1]

    def summarize(field: str) -> dict:
        values = sorted(
            float(value)
            for row in ambiguous
            if (value := getattr(row, field)) is not None
        )
        if not values:
            return {"defined": 0, "mean": None, "max": None, "p50": None, "p95": None}
        def q(frac: float) -> float:
            index = int(round(frac * (len(values) - 1)))
            return values[max(0, min(index, len(values) - 1))]
        return {
            "defined": len(values),
            "mean": sum(values) / len(values),
            "max": values[-1],
            "p50": q(0.50),
            "p95": q(0.95),
        }

    layers = {}
    for round_index, actor in sorted({(row.round_index, row.actor) for row in ambiguous}):
        subset = [row for row in ambiguous if row.round_index == round_index and row.actor == actor]
        defined_cf = [row.uniform_vs_counterfactual_tv for row in subset if row.uniform_vs_counterfactual_tv is not None]
        layers[f"R{round_index}_P{actor}"] = {
            "ambiguous_information_states": len(subset),
            "counterfactual_tv_defined": len(defined_cf),
            "counterfactual_tv_mean": (sum(defined_cf) / len(defined_cf)) if defined_cf else None,
            "counterfactual_tv_max": max(defined_cf) if defined_cf else None,
        }

    return {
        "authority": audit.authority,
        "information_states": audit.information_states,
        "ambiguous_information_states": audit.ambiguous_information_states,
        "uniform_vs_full_tv": summarize("uniform_vs_full_tv"),
        "uniform_vs_counterfactual_tv": summarize("uniform_vs_counterfactual_tv"),
        "full_vs_counterfactual_tv": summarize("full_vs_counterfactual_tv"),
        "layers": layers,
    }


__all__ = [
    "AUTHORITY", "SCHEMA", "ReachAuditRow", "ReachAudit",
    "audit_overlap_conditional_reach", "summarize_overlap_reach",
]
