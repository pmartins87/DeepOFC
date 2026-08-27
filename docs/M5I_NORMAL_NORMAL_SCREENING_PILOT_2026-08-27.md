# M5I Normal/Normal held-out screening pilot — 2026-08-27

Status: `SCREENING_PASS_PIPELINE / STRATEGIC_WEAKNESS_DETECTED / NOT_CERTIFICATION`

This record preserves the first quantitative two-state M5B -> M5I -> M5H screening run after exact M5B candidate materialization was exposed.

## Immutable run identity

- GitHub Actions run: `33081320142`
- workflow: `OpenOFC M5I Normal-Normal screening pilot`
- workflow head: `8f007ecccbca5e4faa1248ca8f8206bc24ac8aa8`
- uploaded artifact id: `9650314134`
- artifact file: `m5i_normal_normal_pilot.json`
- artifact payload SHA-256: `b9ea9a555b2bc5ab9aee52476006ed035877b10e1a8830d6cd630673d464098c`
- uploaded ZIP SHA-256: `4f078890458ef25f98c58cdc192b62caecee1318c8dd24426c5c5667bc667439`
- firewall result: `OPENOFC_M5I_PILOT_FIREWALL=PASS`

The artifact is explicitly `SCREENING_PILOT_NOT_CERTIFICATION`; `ready_for_real_bellman=0` and `certification_claimed=false`.

## Pilot budgets

Candidate M5B per state:

- train-at-current-V iterations: 256
- evaluation samples: 64
- replay capacity: 20,000
- fit epochs: 2
- model buckets: 4,096
- epsilon: 0.6

M5I response screen:

- unilateral-response training iterations: 256 per persistent player
- four independent held-out seeds
- 64 held-out deals per seed
- continuation vector: zero vector

This is an intentionally small diagnostic budget. The numerical values are therefore screening signals, not threshold candidates.

## Results

### `B0:P0F0:P1F0`

Candidate materialization:

- solver infosets: 5,119
- distilled nodes: 4,107
- action examples: 237,492
- mean Huber loss: 0.0859331335
- policy snapshot SHA-256: `57c06c2de269b4f3bf219109daa54be740e57265141bb38fbc5f78e0b3a64fdc`

Held-out M5H aggregate:

- mean profile P0 value: 0.27734375
- seed-level value standard error: 0.4473125317
- P0 maximum learned-response gain: 0.765625
- P1 maximum learned-response gain: 1.15625
- maximum unilateral deviation lower bound: **1.15625**

Per-seed profile/deviation signals:

| seed | profile P0 | P0 gain | P1 gain |
|---|---:|---:|---:|
| `2026082711` | 0.53125 | 0.00000 | 0.00000 |
| `2026082729` | -1.015625 | 0.765625 | 0.00000 |
| `2026082747` | 0.546875 | 0.00000 | 0.25000 |
| `2026082763` | 1.046875 | 0.00000 | 1.15625 |

### `B1:P0F0:P1F0`

Candidate materialization:

- solver infosets: 5,119
- distilled nodes: 4,033
- action examples: 230,868
- mean Huber loss: 0.0884335478
- policy snapshot SHA-256: `d93262f311686dca82996bcf9810367dbd5e5f00ff7ca160f4bf288d57db668f`

Held-out M5H aggregate:

- mean profile P0 value: -0.3046875
- seed-level value standard error: 0.2511772412
- P0 maximum learned-response gain: 1.296875
- P1 maximum learned-response gain: 0.78125
- maximum unilateral deviation lower bound: **1.296875**

Per-seed profile/deviation signals:

| seed | profile P0 | P0 gain | P1 gain |
|---|---:|---:|---:|
| `2026082711` | 0.28125 | 0.00000 | 0.78125 |
| `2026082729` | -0.359375 | 1.296875 | 0.00000 |
| `2026082747` | -0.9375 | 0.59375 | 0.296875 |
| `2026082763` | -0.203125 | 0.00000 | 0.00000 |

## Interpretation

The pipeline itself passed: the exact frozen M5B candidate was screened, the held-out metrics were sealed by M5H, and the M5C firewall correctly refused strategic promotion.

The strategic signal is materially unfavorable at this small budget. A learned unilateral response found gains above one point in both Normal/Normal button states. Because M5I is a lower-bound learned-response method, this does not establish the true exploitability; it does establish that the 256-iteration candidate cannot be treated as close to solved.

The seed-to-seed profile variation is also large, especially for `B0`, so this pilot is too noisy to infer a production value threshold. Increasing held-out samples alone would not address the policy weakness; candidate-training and response-training budgets must also be scaled.

## Decision

Do not expand this exact 256-iteration M5B configuration across the remaining 48 routes as if it were a certification candidate.

Next diagnostic gate:

1. keep the same two Normal/Normal states and zero continuation vector;
2. scale candidate training from 256 to 1,024 iterations;
3. for each frozen candidate, compare 256-iteration versus 1,024-iteration unilateral responses;
4. raise held-out deals to 128 per seed while preserving four independent seeds;
5. use common deterministic seeds so the direction of change is interpretable;
6. remain `HELD_OUT_SCREENING_ONLY` regardless of numerical result.

If stronger candidate training materially reduces the lower-bound deviation while stronger responses do not restore it, continue scaling the candidate. If stronger responses keep exposing roughly point-sized gains, treat the current M5B train/distill architecture as strategically inadequate and diagnose solver/distillation/generalization rather than merely increasing sample counts.
