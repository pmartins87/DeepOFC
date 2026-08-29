# OpenOFC external research — 05G-Q0B results

Date: 2026-08-29  
Branch: `research/external-ofc-solver-audit-20260827`  
Workflow run: `33254595430`  
Workflow job: `99106001637`  
Head commit: `26957d8707a29a52192c22a7a54de8be68e24f49`  
Artifact: `openofc-external-05g-q0b` (`9715421638`)  
Artifact ZIP SHA256: `374439b843ca8a0e12dcfea5b3044f463c289d22e19675b86bbb4f23d07dec3b`  
Manifest SHA256: `558b10979a73ad3e9556a32c246683fbbd787afca6d62e44dc77eaadbc6734a5`

## Verdict

**PASS_SMOKE**

This is a technical result only. It does not rank Search against MCCFR and certifies no production route.

`real_routes_certified = 0`

## Revalidated support

- 36 physical worlds;
- 69,828 reachable information states;
- 69,825 non-root information states;
- 15,393 ambiguous non-root information states;
- exactly 3 P0-R3 root information states;
- no illegal keys;
- no legal-action-set mismatch;
- no invalid/unnormalized distribution;
- no physical `world_id` leakage into information-state keys;
- no policy completion or uniform missing-policy evaluation used.

The frozen 05G support firewall tests also passed `4/4` before the smoke.

## Paired trials

| Search iters | MCCFR iters | Seed | Search non-root coverage | MCCFR non-root coverage | Search ambiguous coverage | MCCFR ambiguous coverage | Root TV range |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2,000 | 64 | 20260829 | 2.3301% | 12.6244% | 10.2969% | 28.0777% | 0.02924–0.03165 |
| 2,000 | 64 | 20260830 | 2.3287% | 12.5929% | 10.2904% | 28.2791% | 0.02903–0.03067 |
| 5,000 | 128 | 20260829 | 2.8170% | 22.2413% | 12.5057% | 44.7606% | 0.01153–0.01229 |
| 5,000 | 128 | 20260830 | 2.7999% | 22.1711% | 12.4277% | 44.6567% | 0.01180–0.01218 |

At the larger paired budget Search materialized about 1,955–1,967 of 69,825 non-root information states, while MCCFR materialized 15,481–15,530.

## Root diagnostic

All three root information states were materialized by both learners in all four trials.

For each of the three private R3 packet types, both algorithms selected the same dominant public placement geometry: place `7c` and `8c` on bottom and discard the third private card (`8h`, `9d`, or `Td`, depending on the packet).

At 5,000 Search iterations the dominant Search root action had probability approximately `0.9877–0.9885`; MCCFR's current regret-matching policy was pure (`1.0`) on the same action in these trials. Root total-variation disagreement fell to roughly `0.0115–0.0123`.

This agreement is diagnostic only. It does not imply comparable downstream policy quality or low exploitability.

## Work/runtime

On the GitHub Ubuntu runner:

- Search 2,000: about 3.05–3.07 s per seed;
- MCCFR 64: about 3.74–3.76 s per seed, 13,824 terminal evaluations;
- Search 5,000: about 7.59 s per seed;
- MCCFR 128: about 7.49–7.51 s per seed, 27,648 terminal evaluations.

The complete Q0B runner finished in about 72 seconds after the support tests.

## Scientific reading

Q0B exposes a concrete architecture fact that was not visible from root policy alone:

- Search and MCCFR are already very close at the three root decisions;
- their **downstream native coverage is not close**;
- MCCFR materializes information sets much more broadly under comparable wall-clock work on this reduced fixture;
- Search remains heavily concentrated on its own sampled trajectories.

Therefore the next gate must not compare completed policies until the completion treatment is explicit and symmetric. Otherwise a large fraction of the apparent Search policy would actually be the completion algorithm rather than Search itself.

## Next step

Proceed to 05G-Q0C as a precommitted **coverage/scaling diagnostic**, still without strategic ranking. Its purpose is to determine whether the native-coverage gap persists under larger but bounded budgets and to quantify which layers remain uncovered before designing Q1 completion/router experiments.

No current DeepOFC strategic component is replaced by this result.
