# M5N Normal×Fantasy runtime calibration — F14

Date: 2026-08-27

## Result

Workflow `33113775256`: **PASS**.

Artifact payload SHA-256:

`2ecfe913abf6d7d0c7ef8697be55ec9733515731b470cd0b778345de8258847e`

Artifact ZIP digest:

`sha256:1a2eeafd733c5a9dbccdb609fd20df6727789eef37a6e143d5112a21021478ea`

Durable payload:

`evidence/strategic/m5n_runtime_calibration_f14_2026-08-27.json`

## What the calibration measured

Representative route: `B0:P0F0:P1F14`.

Reduced calibration budgets:

- candidate training: 8 iterations;
- challenger training: 16 iterations;
- held-out: 4 seeds × 4 paired samples;
- total exact terminal evaluations: 56.

Measured wall time:

- candidate materialization: `16.818771032 s` for 8 exact terminal evaluations;
- challenger materialization: `17.294272649 s` for 16 exact terminal evaluations;
- paired screening: `50.263919871 s` for 32 exact terminal evaluations;
- total measured: `84.376967938 s`.

Exact-terminal cache behavior:

- hits: `0`;
- misses: `56`.

The paired held-out phase was the largest single phase in this reduced run. The calibration screening result itself has no strategic authority; the budgets were intentionally tiny and the artifact explicitly says `RUNTIME_CALIBRATION_NOT_STRATEGIC_EVIDENCE`.

## What this says about the cancelled full pilot

The original full M5N pilot used, per route:

- 256 candidate iterations;
- 1024 challenger iterations;
- 4 × 128 held-out samples, with candidate and challenger both evaluated on every sample.

That is approximately 2,304 exact terminal evaluations per route, 4,608 across the two original routes. The F14 calibration confirms that the exact Normal×Fantasy terminal evaluator is the dominating unit of work and that unique sampled plans receive essentially no cache reuse.

A simple linear projection from this F14 calibration gives roughly:

- candidate phase: ~9.0 minutes;
- challenger phase: ~18.4 minutes;
- paired screen: ~26.8 minutes;
- total F14 route: ~54 minutes.

This projection is a scheduling estimate only, not measured strategic evidence. It strongly suggests that running both F14 and F17 serially in one 180-minute job was a poor execution layout, and that the 17-card route needs its own calibration because its exact terminal cost may be materially higher.

## Decision

1. Preserve run `33089463461` as a runtime-feasibility timeout, not a strategy failure.
2. Calibrate the `F17` route independently with the same reduced phase-timed budget.
3. If F17 is individually compatible with the Actions limit, rerun the original strategic budgets as **one route per job**, in parallel, rather than serially.
4. If F17 itself is too expensive, profile/optimize its exact terminal evaluator before spending another full strategic budget.
5. Do not lower strategic M5N budgets merely to obtain a green run.

REAL strategic route count remains `0/50`.
