# OpenOFC external research — 05H-H0 results (2026-08-29)

Authority: `BROADER_HIDDEN_INFORMATION_REDUCED_GAME_SHADOW_ONLY`  
Production authority: **none**  
REAL routes certified: **0**

## Run

- Workflow: `OpenOFC external 05H H0 144-world geometry`
- Run: `33272075265`
- Job: `99152230102`
- Immutable run head: `80ef5b893ea6d90cf5a9331351da8dabbc4e4f48`
- Conclusion: `success`
- Artifact: `openofc-external-05h-h0`, id `9720414813`
- Artifact ZIP SHA-256: `fdc91a3d33c13361c887d5bb6b8d4aff52ab80f8c360567a40926a149cd0dc61`
- Manifest SHA-256: `706fc03080d7d6a98fcda396c723fcec449ae5871be04631784856adb6459ed7`

## Frozen support

The geometry-only 4×4×3×3 Cartesian schedule produced exactly **144 physical worlds**. All physical-support invariants passed before the exhaustive tree was materialized.

Support SHA-256: `ba8bf94e0c5c6eec01ad2ee54a32b6437603c5061c1e6f07e4650977f82c5ec9`.

## Exact exhaustive geometry

- reachable information states: **261,076**
- ambiguous information states: **43,348**
- ambiguous non-root information states: **43,344**
- non-root infosets with >=3 compatible concrete states: **43,344**
- maximum compatible concrete states in one infoset: **36**
- hidden-discard collision for P0: **yes**
- hidden-discard collision for P1: **yes**

Per layer:

| Layer | Infosets | Ambiguous | Max compatible states |
|---|---:|---:|---:|
| R3-P0 | 4 | 4 | 36 |
| R3-P1 | 252 | 252 | 36 |
| R4-P0 | 15,876 | 15,876 | 12 |
| R4-P1 | 244,944 | 27,216 | 4 |

## Expansion versus 05G

The support was chosen before any 05H payoff was observed and passed every precommitted broadening criterion:

- worlds: **36 → 144 (4×)**;
- reachable infosets: **69,828 → 261,076 (~3.739×)**;
- ambiguous non-root infosets: **15,393 → 43,344 (~2.816×)**;
- non-root infosets with >=3 compatible states: **10,101 → 43,344 (~4.291×)**;
- maximum compatible-state multiplicity: **12 → 36 (3×)**.

The dominant state-space growth is R4-P1: **244,944** reachable infosets. This is useful because it materially increases the counterfactual-completeness burden rather than merely adding duplicate chance roots.

## Runtime

- physical validation: **0.0057 s**
- exhaustive support materialization: **103.4793 s**
- geometry/collision summary: **0.2014 s**
- total H0 core runtime: **103.6865 s**

Therefore the fourfold chance-support expansion remains practical on standard GitHub-hosted CPU for exact support construction.

## Verdict

**`PASS_05H_H0_GEOMETRY`**.

No strategy was trained, no terminal payoff was inspected, and no best response or exploitability was computed in H0. The frozen routing is therefore activated: **05H-H1 MCCFR native coverage calibration**, using the budget ladder and thresholds committed before this H0 result was known.