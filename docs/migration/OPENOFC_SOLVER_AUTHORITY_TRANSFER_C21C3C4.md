# OpenOFC solver authority transfer — c21c3c4

Date: 2026-08-27
Status: **COMPLETE**

This document is the final repository-authority record for the provenance-preserving migration of the M4/M5 OpenOFC strategic solver tree from the temporary OpenHoldem staging repository into DeepOFC.

## Frozen source provenance

- source repository: `pmartins87/myoh_private`
- source commit: `c21c3c4f1017c83df07eb22230318a8131bf40d1`
- source solver tree: `73523862dac5b704d6f9878edefaa36212f20bc9`
- source role after transfer: **immutable historical strategic provenance**

## Corrected migration identity

The first inventory implementation was intentionally superseded after the behavioral gate exposed that it had not recomputed dependencies introduced by matching tests. `test_engine.py` required `teacher_search.py`; the first equivalence attempt therefore passed 19/20 and failed closed on the migrated side.

The corrected inventory uses a fixed-point closure and is authoritative:

- inventory schema: `deepofc-openofc-solver-inventory-v2`
- frozen solver-subtree files: **187**
- migrate: **126**
- historical: **61**
- related M4/M5 workflows: **38**
- inventory payload SHA-256: `06df84fa80c6bf869125ec858551b84c00895b4230c07079aa0b20eaa8b8c007`
- corrected inventory workflow run: `33070689091` — **PASS**

## Pure migration / provenance

- corrected pure-migration workflow run: `33070802793` — **PASS**
- migrated files: **126**
- source/target byte identity: **126/126 true**
- provenance canonical SHA-256: `4041f7560f9a94b5e85b9c1c986f39e690bca5e3635328fad1bff1fdd1b11766`
- materialized solver commit: `0c0ae8d77c8ca35c344f59c1515f6712b2ca1a2a`

## Deterministic behavioral equivalence

- workflow run: `33070910873` — **PASS**
- frozen source PASS: **20/20**
- migrated target PASS: **20/20**
- normalized stdout/stderr equality: **20/20**
- equivalence report SHA-256: `935162877ad8f7821fa106ba7cd2f5bfc588a60f2273c34443eb805926e93664`
- persisted evidence commit: `d45a9b77df8d75c1feaf45c8354ea152cd311355`

## Canonical DeepOFC CI and merge

The first PR-level DeepOFC CI attempt correctly failed because the newly migrated solver tests introduced a NumPy dependency that was not yet present in the repository-level `requirements-dev.txt`. This was an integration/dependency declaration defect, not a solver behavior failure.

The canonical test dependency was then declared as `numpy==2.4.6`, matching the successful migration/equivalence environment.

- PR: `#13` — `DeepOFC: transfer OpenOFC solver authority after provenance and equivalence PASS`
- corrected PR-level canonical CI run: `33074562167` — **PASS**
- PR head at merge: `c364a3056349ba627f273265c7c7a742b2d72c99`
- merge commit: `4842d01dc68b14bae5a083d8ae0138297d7a0783`
- post-merge `main` canonical CI run: `33074839933` — **PASS**

## Authority decision

**G1–G6 are complete.**

From merge commit `4842d01dc68b14bae5a083d8ae0138297d7a0783` onward:

- `pmartins87/DeepOFC`, branch `main`, is the active strategic source authority for the migrated M4/M5 solver tree;
- `pmartins87/myoh_private@c21c3c4...` remains frozen historical provenance;
- future strategic development belongs in DeepOFC;
- the runtime repository should consume explicit versioned/exported policy artifacts rather than become the sole owner of strategic source.

## What this does not prove

Repository authority transfer, byte identity and deterministic behavioral equivalence do **not** prove strategic optimality, bounded exploitability or production readiness.

The next substantive strategic gate remains real held-out evidence and state-local certification for all **50 exact-V routes**:

- 2 Normal × Normal;
- 16 Normal × Fantasy;
- 32 Fantasy × Fantasy.

Only after 50/50 real certification may M5G build a real-ready registry and enable the first REAL dynamic M4Z Bellman trace.
