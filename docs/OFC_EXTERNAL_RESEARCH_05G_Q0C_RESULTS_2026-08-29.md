# OpenOFC external research — 05G-Q0C results

Date: 2026-08-29  
Branch: `research/external-ofc-solver-audit-20260827`  
Workflow run: `33254756358`  
Workflow job: `99106416878`  
Head commit: `b996f7fc3397d30cd5a2ced648728df5f28f17b7`  
Artifact: `openofc-external-05g-q0c` (`9715524968`)  
Artifact ZIP SHA256: `7f2784b4904dbc5c5a612bf2d0668b684003ba2a715d4a1d94caa3e8385014de`  
Manifest SHA256: `6d05400a0ffd136cb4872bdd8a61d535090e0e967300d161219675ab4f480500`

## Verdict

**PASS_SCALING_DIAGNOSTIC**

This remains a shadow engineering result. It does not rank strategic strength and certifies no production route.

`real_routes_certified = 0`

## Frozen support

- 36 physical worlds;
- 69,828 reachable information states;
- 69,825 non-root information states;
- 15,393 ambiguous non-root information states;
- 3 P0-R3 root information states;
- all semantic/profile-validation firewalls remained green;
- support tests passed `4/4` before the scaling run.

## Native-coverage scaling

| Learner | Budget | Seed | Non-root coverage | Ambiguous non-root coverage | Runtime |
|---|---:|---:|---:|---:|---:|
| Search | 20,000 | 20260829 | 1,986 / 69,825 = **2.8443%** | 1,944 / 15,393 = **12.6291%** | 29.17 s |
| Search | 20,000 | 20260830 | 1,987 / 69,825 = **2.8457%** | 1,945 / 15,393 = **12.6356%** | 29.36 s |
| Search | 50,000 | 20260829 | 1,986 / 69,825 = **2.8443%** | 1,944 / 15,393 = **12.6291%** | 72.70 s |
| Search | 50,000 | 20260830 | 1,987 / 69,825 = **2.8457%** | 1,945 / 15,393 = **12.6356%** | 72.89 s |
| MCCFR | 256 | 20260829 | 26,016 / 69,825 = **37.2589%** | 10,145 / 15,393 = **65.9066%** | 14.47 s |
| MCCFR | 256 | 20260830 | 25,715 / 69,825 = **36.8278%** | 9,872 / 15,393 = **64.1330%** | 14.48 s |
| MCCFR | 512 | 20260829 | 39,794 / 69,825 = **56.9910%** | 13,110 / 15,393 = **85.1686%** | 28.88 s |
| MCCFR | 512 | 20260830 | 39,657 / 69,825 = **56.7948%** | 12,962 / 15,393 = **84.2071%** | 28.88 s |

MCCFR terminal work was 55,296 evaluations at 256 iterations and 110,592 at 512.

## Layer coverage

### Search — seed 20260829

The 20k and 50k snapshots are **identical in materialized support**:

- P0-R3: `3/3 = 100%`;
- P1-R3: `60/147 = 40.8163%`;
- P0-R4: `354/6,174 = 5.7337%`;
- P1-R4: `1,572/63,504 = 2.4754%`.

### Search — seed 20260830

Again 20k and 50k are **identical in materialized support**:

- P0-R3: `3/3 = 100%`;
- P1-R3: `61/147 = 41.4966%`;
- P0-R4: `354/6,174 = 5.7337%`;
- P1-R4: `1,572/63,504 = 2.4754%`.

### MCCFR — 512 iterations

Seed 20260829:

- P0-R3: `3/3 = 100%`;
- P1-R3: `147/147 = 100%`;
- P0-R4: `4,864/6,174 = 78.7820%`;
- P1-R4: `34,783/63,504 = 54.7729%`.

Seed 20260830:

- P0-R3: `3/3 = 100%`;
- P1-R3: `147/147 = 100%`;
- P0-R4: `4,833/6,174 = 78.2799%`;
- P1-R4: `34,677/63,504 = 54.6060%`.

## Search saturation is the key result

For both frozen seeds, increasing Search from **20,000 to 50,000 iterations added exactly zero new information states**. Runtime increased from about 29 seconds to about 73 seconds, while every layer count remained byte-for-byte unchanged at the support-count level.

This is stronger evidence than a merely slow coverage curve. On this fixture the current UCT policy becomes trapped in a narrow on-policy trajectory basin: additional iterations refine visits inside already discovered information states instead of expanding downstream native policy support.

Root concentration continues to improve: Search-vs-MCCFR root TV fell to roughly `0.00118–0.00121` in the 50k/512 trials. Therefore the root is no longer the relevant uncertainty; off-trajectory completeness is.

## Search/MCCFR native support overlap

At 20k/256:

- seed 20260829: intersection `1,919`, Jaccard `0.07356`; **96.48%** of Search keys were also present in MCCFR;
- seed 20260830: intersection `1,912`, Jaccard `0.07412`; **96.08%** of Search keys were also present in MCCFR.

At 50k/512:

- seed 20260829: intersection `1,952`, Jaccard `0.04900`; **98.14%** of Search keys were also present in MCCFR, but only **4.90%** of MCCFR keys were present in Search;
- seed 20260830: intersection `1,956`, Jaccard `0.04928`; **98.29%** of Search keys were also present in MCCFR, but only **4.93%** of MCCFR keys were present in Search.

The decreasing Jaccard is not a regression: MCCFR is expanding far beyond the small Search support.

## Scientific interpretation

Q0C establishes an architecture constraint for the next experiment:

1. raw additional UCT iterations are not a plausible route to policy completeness on this fixture;
2. Search remains useful as a concentrated on-path/root decision mechanism;
3. MCCFR is substantially more effective as a broad information-set materializer under comparable wall-clock work;
4. this does **not** prove MCCFR is strategically stronger — no exact bilateral best response was run;
5. any Q1 evaluation must expose completion/backfill as an explicit third component with source provenance at every information set.

A completed Search policy cannot be described as “Search” if more than 97% of the exhaustive support came from an undeclared fallback/completion mechanism.

## Next experiment

Proceed in parallel with:

- **05G-Q0D MCCFR-only scaling**, to determine how much of the remaining ~43% support can be covered natively before introducing completion;
- **05G-Q1 completion/router design**, with immutable native decisions and explicit per-infoset provenance (`SEARCH_NATIVE`, `MCCFR_NATIVE`, `COMPLETION`).

No DeepOFC production component is replaced by this result.
