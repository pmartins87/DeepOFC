from __future__ import annotations

"""Exact finite-support conditional reach diagnostics for 05D-Q2.

Authority:
  FINITE_SUPPORT_CONDITIONAL_REACH_AUDIT_ONLY
"""

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence

from external_two_street_infoset_search import TwoStreetWorld, _assert_root_isolation, _with_world
from strategic_cfr import HUState, child_state, information_state_key, legal_action_pairs

AUTHORITY = "FINITE_SUPPORT_CONDITIONAL_REACH_AUDIT_ONLY"
SCHEMA = "openofc-external-two-street-reach-audit-v1"
ReadOnlyProfile = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class ConditionalReachRow:
    information_state_key: str
    round_index: int
    actor: int
    compatible_states: int
    full_reach_weights: tuple[tuple[str, float], ...]
    counterfactual_reach_weights: tuple[tuple[str, float], ...]
    uniform_vs_full_tv: float
    uniform_vs_counterfactual_tv: float
    full_vs_counterfactual_tv: float
    full_max_weight: float
    counterfactual_max_weight: float
    full_effective_support: float
    counterfactual_effective_support: float


@dataclass(frozen=True)
class ConditionalReachAudit:
    authority: str
    support_worlds: int
    information_states: int
    rows: tuple[ConditionalReachRow, ...]


def _distribution(
    profile: ReadOnlyProfile,
    info_key: str,
    action_keys: Sequence[str],
) -> dict[str, float]:
    legal = tuple(action_keys)
    supplied = profile.get(info_key)
    if supplied is None:
        raise ValueError(f"reach audit requires an explicit policy at infoset: {info_key}")
    illegal = set(supplied) - set(legal)
    if illegal:
        raise ValueError(f"profile contains illegal actions: {sorted(illegal)}")
    weights: dict[str, float] = {}
    for key in legal:
        value = float(supplied.get(key, 0.0))
        if value < 0.0 or not math.isfinite(value):
            raise ValueError("profile probabilities must be finite and non-negative")
        weights[key] = value
    mass = sum(weights.values())
    if mass <= 0.0:
        raise ValueError("reach audit refuses zero-mass explicit policy")
    return {key: value / mass for key, value in weights.items()}


def _normalize(weights: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
    positive = {key: float(value) for key, value in weights.items() if value > 0.0}
    mass = sum(positive.values())
    if mass <= 0.0:
        return ()
    return tuple((key, positive[key] / mass) for key in sorted(positive))


def _tv(
    p: Mapping[str, float],
    q: Mapping[str, float],
) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(float(p.get(key, 0.0)) - float(q.get(key, 0.0))) for key in keys)


def _effective_support(weights: Mapping[str, float]) -> float:
    denom = sum(value * value for value in weights.values())
    return (1.0 / denom) if denom > 0.0 else 0.0


def audit_conditional_reach(
    base_state: HUState,
    worlds: Iterable[TwoStreetWorld],
    *,
    profile: ReadOnlyProfile,
) -> ConditionalReachAudit:
    """Exactly enumerate full and acting-player counterfactual reach weights."""
    support = tuple(worlds)
    if len(support) < 2:
        raise ValueError("reach audit requires at least two physical worlds")
    _assert_root_isolation(base_state, support)

    # info_key -> concrete fingerprint -> [full reach, counterfactual reach]
    accum: dict[str, dict[str, list[float]]] = {}
    metadata: dict[str, tuple[int, int]] = {}
    chance = 1.0 / len(support)

    def walk(state: HUState, reach_p0: float, reach_p1: float) -> None:
        if state.terminal():
            return
        info_key = information_state_key(state)
        actor = state.actor
        meta = (state.round_index, actor)
        previous = metadata.get(info_key)
        if previous is None:
            metadata[info_key] = meta
        elif previous != meta:
            raise AssertionError("information-state key collided across actor/round")

        full = chance * reach_p0 * reach_p1
        counterfactual = chance * (reach_p1 if actor == 0 else reach_p0)
        fingerprint = repr(state)
        bucket = accum.setdefault(info_key, {}).setdefault(fingerprint, [0.0, 0.0])
        bucket[0] += full
        bucket[1] += counterfactual

        pairs = tuple(legal_action_pairs(state))
        action_keys = tuple(key for key, _action in pairs)
        distribution = _distribution(profile, info_key, action_keys)
        by_key = dict(pairs)
        for action_key in action_keys:
            probability = distribution[action_key]
            if probability <= 0.0:
                continue
            if actor == 0:
                walk(child_state(state, by_key[action_key]), reach_p0 * probability, reach_p1)
            else:
                walk(child_state(state, by_key[action_key]), reach_p0, reach_p1 * probability)

    for world in support:
        walk(_with_world(base_state, world), 1.0, 1.0)

    rows: list[ConditionalReachRow] = []
    for info_key in sorted(accum):
        state_weights = accum[info_key]
        full_raw = {fingerprint: values[0] for fingerprint, values in state_weights.items()}
        cf_raw = {fingerprint: values[1] for fingerprint, values in state_weights.items()}
        full_norm_tuple = _normalize(full_raw)
        cf_norm_tuple = _normalize(cf_raw)
        full_norm = dict(full_norm_tuple)
        cf_norm = dict(cf_norm_tuple)
        concrete = sorted(set(full_raw) | set(cf_raw))
        uniform = {fingerprint: 1.0 / len(concrete) for fingerprint in concrete}
        round_index, actor = metadata[info_key]
        rows.append(
            ConditionalReachRow(
                information_state_key=info_key,
                round_index=round_index,
                actor=actor,
                compatible_states=len(concrete),
                full_reach_weights=full_norm_tuple,
                counterfactual_reach_weights=cf_norm_tuple,
                uniform_vs_full_tv=_tv(uniform, full_norm),
                uniform_vs_counterfactual_tv=_tv(uniform, cf_norm),
                full_vs_counterfactual_tv=_tv(full_norm, cf_norm),
                full_max_weight=max(full_norm.values(), default=0.0),
                counterfactual_max_weight=max(cf_norm.values(), default=0.0),
                full_effective_support=_effective_support(full_norm),
                counterfactual_effective_support=_effective_support(cf_norm),
            )
        )

    return ConditionalReachAudit(
        authority=AUTHORITY,
        support_worlds=len(support),
        information_states=len(rows),
        rows=tuple(rows),
    )


def summarize_reach_audit(audit: ConditionalReachAudit) -> dict:
    def summary(values: Sequence[float]) -> dict[str, float]:
        ordered = sorted(float(value) for value in values)
        if not ordered:
            return {"mean": 0.0, "max": 0.0, "p50": 0.0, "p95": 0.0}
        def quantile(q: float) -> float:
            index = int(round(q * (len(ordered) - 1)))
            return ordered[max(0, min(index, len(ordered) - 1))]
        return {
            "mean": sum(ordered) / len(ordered),
            "max": ordered[-1],
            "p50": quantile(0.50),
            "p95": quantile(0.95),
        }

    multi = [row for row in audit.rows if row.compatible_states > 1]
    layers: dict[str, dict] = {}
    for round_index, actor in sorted({(row.round_index, row.actor) for row in audit.rows}):
        subset = [row for row in audit.rows if row.round_index == round_index and row.actor == actor]
        key = f"R{round_index}_P{actor}"
        layers[key] = {
            "information_states": len(subset),
            "multi_state_information_states": sum(1 for row in subset if row.compatible_states > 1),
            "uniform_vs_full_tv": summary([row.uniform_vs_full_tv for row in subset]),
            "uniform_vs_counterfactual_tv": summary([row.uniform_vs_counterfactual_tv for row in subset]),
            "full_vs_counterfactual_tv": summary([row.full_vs_counterfactual_tv for row in subset]),
        }
    return {
        "authority": audit.authority,
        "support_worlds": audit.support_worlds,
        "information_states": audit.information_states,
        "multi_state_information_states": len(multi),
        "uniform_vs_full_tv": summary([row.uniform_vs_full_tv for row in multi]),
        "uniform_vs_counterfactual_tv": summary([row.uniform_vs_counterfactual_tv for row in multi]),
        "full_vs_counterfactual_tv": summary([row.full_vs_counterfactual_tv for row in multi]),
        "layers": layers,
    }


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "ConditionalReachRow",
    "ConditionalReachAudit",
    "audit_conditional_reach",
    "summarize_reach_audit",
]
