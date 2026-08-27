# OpenOFC solver old-vs-new equivalence

Status: **PASS**

- suite: `openofc-migration-equivalence-2026-08-27-v1`
- frozen source: `pmartins87/myoh_private@c21c3c4f1017c83df07eb22230318a8131bf40d1`
- target gate-start commit: `dd5839c364e7a9d18b97ab580c1ad38d9814ac9f`
- Python: `3.11.16`
- NumPy: `2.4.6`
- tests: **20**
- matched: **20**
- canonical report SHA-256: `935162877ad8f7821fa106ba7cd2f5bfc588a60f2273c34443eb805926e93664`

| Test | Source | Target | Transcript | Result |
|---|---:|---:|---|---|
| `test_engine.py` | 0 | 0 | equal | PASS |
| `test_hu_continuation.py` | 0 | 0 | equal | PASS |
| `test_m4u_continuation_boundary.py` | 0 | 0 | equal | PASS |
| `test_m4v_continuation_targets.py` | 0 | 0 | equal | PASS |
| `test_m4w_outcome_model.py` | 0 | 0 | equal | PASS |
| `test_m4x_robust_support.py` | 0 | 0 | equal | PASS |
| `test_m4y_bellman_trace.py` | 0 | 0 | equal | PASS |
| `test_m4z_outer_bellman.py` | 0 | 0 | equal | PASS |
| `test_m5a_component_adapters.py` | 0 | 0 | equal | PASS |
| `test_m5a_normal_fantasy_oracle.py` | 0 | 0 | equal | PASS |
| `test_m5b_fantasy_selfplay.py` | 0 | 0 | equal | PASS |
| `test_m5c_route_certification.py` | 0 | 0 | equal | PASS |
| `test_m5c_normal_route_certification.py` | 0 | 0 | equal | PASS |
| `test_m5d_dynamic_certified_bellman.py` | 0 | 0 | equal | PASS |
| `test_m5e_fantasy_route_certification.py` | 0 | 0 | equal | PASS |
| `test_m5f_fantasy_heldout_evidence.py` | 0 | 0 | equal | PASS |
| `test_m5g_full_registry_factory.py` | 0 | 0 | equal | PASS |
| `test_normal_fantasy_kernel.py` | 0 | 0 | equal | PASS |
| `test_fantasy_fantasy_kernel.py` | 0 | 0 | equal | PASS |
| `test_fantasy_fantasy_payoff.py` | 0 | 0 | equal | PASS |

The comparison runs the two repositories independently with fixed process/thread environment and requires zero exit status plus byte-identical normalized stdout/stderr for every predeclared test.
