# M5J Normal/Normal budget ladder — 2026-08-27

Status: `PIPELINE_PASS / RESPONSE_GENERALIZATION_WARNING / NOT_CERTIFICATION`

GitHub Actions run: `33083102421`

Artifact: `openofc-m5j-normal-normal-budget-ladder`

Artifact id: `9652507175`

Artifact ZIP digest: `sha256:9f456d041a7382eaf98434a39907f24043949997c9b0405f8d8e49cafc056979`

Artifact payload SHA-256: `533f17a7ed0394339c14c2c89d86e57ff85ff487dfd9622f021fd3f56e1fe181`

Downloaded raw JSON SHA-256: `e61869801a0b89c60b572a50d3c0ee105b0093cff6ec29a30d22b19c56c88d01`

## Results

| state | candidate | response | max deviation diagnostic | profile-value SE |
|---|---:|---:|---:|---:|
| `B0:P0F0:P1F0` | 256 | 256 | 1.140625 | 0.243538320 |
| `B0:P0F0:P1F0` | 256 | 1024 | 1.140625 | 0.243538320 |
| `B0:P0F0:P1F0` | 1024 | 256 | 0.875000 | 0.150728449 |
| `B0:P0F0:P1F0` | 1024 | 1024 | 0.875000 | 0.150728449 |
| `B1:P0F0:P1F0` | 256 | 256 | 0.5390625 | 0.090576720 |
| `B1:P0F0:P1F0` | 256 | 1024 | 0.5390625 | 0.090576720 |
| `B1:P0F0:P1F0` | 1024 | 256 | 0.734375 | 0.214034342 |
| `B1:P0F0:P1F0` | 1024 | 1024 | 0.734375 | 0.214034342 |

Candidate scaling is not monotone across the two button states: B0 improves numerically while B1 worsens. This is not enough evidence that four-times-more M5B training reliably improves the candidate.

## Response-budget warning

The 256- and 1,024-response rows are numerically identical for each frozen candidate, including every seed-level metric. At the same time, response training grows from 1,280 visited infosets per player to about 5,117–5,120.

The current M5I code returns a uniform policy when a held-out visible infoset is absent from the tabular response-training dictionary. It currently has no generalizer for unseen response infosets. In a very large OpenOFC information space, exact overlap between response-training deals and disjoint held-out deals may therefore be extremely small.

This must be measured directly before interpreting M5I/M5J as a calibrated approximate best response.

## Uncertainty warning

The current screen also does not report uncertainty for the response-minus-candidate gain itself. Candidate and response rollouts use different action-randomness seeds, negative sample-mean gains are clipped to zero, and the largest seed-level gain is retained. The existing `value_standard_error` applies to candidate profile value, not to deviation gain.

## Next gate

1. measure exact held-out response-infoset hit/fallback rates;
2. add visible-state generalization to the response policy;
3. use paired/common-random-number candidate-versus-response evaluation;
4. report signed paired gain and its uncertainty;
5. calibrate the generalized response mechanism against M5L exact BR.

All M5I/M5J results remain `HELD_OUT_SCREENING_ONLY`. They do not certify exploitability or any REAL M4Z route.
