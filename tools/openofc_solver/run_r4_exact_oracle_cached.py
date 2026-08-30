from __future__ import annotations

import json
from time import perf_counter

from external_06r0_conditioned_solver import FROZEN_FIXTURES, build_conditioned_fixture
from external_06r1_belief_correct import build_belief_support
from r4_exact_oracle_cached import cache_info, exact_r4_p0_oracle_cached


def main() -> None:
    spec = next(x for x in FROZEN_FIXTURES if x.name == "R4_P0_A")
    root = build_conditioned_fixture(spec)
    started = perf_counter()
    support = build_belief_support(root, spec)
    support_seconds = perf_counter() - started
    started = perf_counter()
    oracle = exact_r4_p0_oracle_cached(root, spec, support)
    oracle_seconds = perf_counter() - started
    print(json.dumps({
        "support_seconds": support_seconds,
        "hidden_history_count": support.hidden_history_count,
        "oracle_seconds": oracle_seconds,
        "posterior_worlds": oracle.posterior_worlds,
        "best_action_key": oracle.best_action_key,
        "best_value": oracle.best_value,
        "root_action_values": dict(oracle.root_action_values),
        "p1_information_states_by_root_action": dict(oracle.p1_information_states_by_root_action),
        "cache_info": cache_info(),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
