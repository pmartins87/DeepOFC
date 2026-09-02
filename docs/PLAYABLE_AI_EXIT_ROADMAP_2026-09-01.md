# DeepOFC — finite roadmap to first strong playable AI

Date: 2026-09-01
Branch: `research/external-ofc-solver-audit-20260827`
Status: **critical-path contract**

## Why this document exists

The project accumulated increasingly rigorous certification research. That work
is useful, but formal full-game certification is no longer allowed to expand the
critical path indefinitely before a strong AI can actually play.

From this point forward the project has two lanes:

1. **PLAYABLE** — finite path to a strong deterministic candidate that can make
   and execute legal decisions end-to-end. This is the critical path.
2. **FORMAL** — M5R/M5H/M5C and REAL route certification. This continues as a
   separate research/certification lane and cannot invent new PLAYABLE blockers
   unless it exposes a concrete rules/scoring/legal bug or a material strategic
   weakness.

## Admission rule for new critical-path work

A new task may enter PLAYABLE only if at least one is true:

- it can change an AI action materially;
- it exposes or fixes a rules/scoring/legal/information-state error;
- it demonstrates measurable strategic improvement under a frozen benchmark;
- it is required for deterministic state -> policy -> action -> execution wiring.

Scientific interest alone is not sufficient.

## Stage P1 — close concrete mechanics/scoring defects

**Goal:** one trusted Normal x Normal strategic objective.

Required:

- [x] Canonical physical 54-card state and legal action engine exist.
- [x] Project-frozen Joker scoring uses independent nominal substitution with
      replacement and excludes Five-of-a-Kind.
- [x] External-sampling MCCFR selected over ISUCT on the certified three-round
      V2 architecture benchmark.
- [x] Concrete continuation scorer discrepancy (`legacy 0` vs canonical `+/-1`)
      diagnosed as stale no-replacement Joker scoring in migrated
      `tools/openofc_solver/engine.py`.
- [x] Continuation immediate terminal score rerouted to canonical
      `deepofc.scoring`.
- [x] Normal -> Fantasy entry in the continuation path rerouted to canonical
      QQ/KK/AA/Top-trips = 14/15/16/17 semantics.
- [x] Focused regression/full continuation validation after the fix is green:
      GitHub Actions run `33457670822`, verdict
      `PASS_M5R_CONTINUATION_TRANSFER_VALIDATION`, 4/4 cells green,
      3,389,236 independently crosschecked unique terminal states.
- [x] Simultaneous both-foul is isolated as an explicit PLAYABLE-only
      `MUTUAL_AUTO_SCOOP_NET_ZERO_INFERENCE`; the canonical scorer remains
      fail-closed because the official KKPoker page does not state this edge
      case directly.

**P1 exit:** no silent Normal x Normal scoring/legal mismatch remains in the
training/decision objective. The one unresolved official-source edge case is
named, hash-bound and replaceable rather than being presented as canonical law.

## Stage P2 — materialize one immutable strong MCCFR candidate

**Goal:** stop talking about an abstract solver and produce one policy artifact.

Required:

- freeze training code commit and configuration;
- freeze RNG seed(s), training work budget and continuation objective identity;
- train the selected external-sampling MCCFR Normal x Normal candidate;
- export the complete deployable average-policy snapshot;
- write immutable SHA-256 + schema + source commit + objective fingerprint;
- deterministic reload test: exported snapshot reproduces policy probabilities
  and selected actions byte-for-byte/within the frozen numeric tolerance;
- run one final bounded strategic sanity battery: legality, deterministic replay,
  benchmark exploitability/deviation checks already available, and no regression
  against the selected R6/06R3 architecture baseline.

No new solver family comparison is permitted here unless the frozen candidate
fails a concrete strategic acceptance criterion.

Implementation status:

- [x] deterministic route exporter/reloader and tamper checks implemented;
- [x] complete visible-information generalizer payload, objective, configuration,
      seeds, source commit, snapshot and materialization identities are bound;
- [x] B0/B1 aggregate manifest and non-certification firewall implemented;
- [x] frozen 4,096-iteration B0/B1 training workflow completed and artifact SHA
      preserved: run `33597399958`, manifest
      `f10c079a61ba08832cfc334afb9c055e023dfc9c23a24140d02b2f7bd8413898`;

**P2 exit:** one immutable policy artifact exists and can answer a canonical
Normal x Normal decision state deterministically.

## Stage P3 — wire policy to the runtime and prove end-to-end play

**Goal:** first actual playable AI.

Required:

- define/export the canonical observation -> policy infoset/state-key adapter;
- verify every selected action is legal for the observed state;
- bind policy artifact SHA, DeepOFC source commit, OpenHoldem runtime commit,
  tablemap/recognizer identity and runtime build artifact;
- deterministic replay: recorded table state -> canonical state -> policy action
  -> drag plan -> post-action verification;
- shadow mode on recorded/controlled hands before live execution;
- one controlled end-to-end Normal x Normal hand path with fail-closed behavior
  on ambiguous recognition.

**PLAYABLE DONE:** a frozen policy candidate, identified by SHA, consumes a
recognized canonical Normal x Normal state, chooses a legal action, and the
runtime executes/verifies that action deterministically end-to-end.

At PLAYABLE DONE the AI is usable as a first strong candidate. It is not claimed
to be formally Nash-certified or production-complete for all 50 continuation
states.

## Explicitly outside the PLAYABLE critical path

These remain valuable but cannot delay P2/P3 unless they expose a concrete bug:

- completing every M5R interval/certification experiment;
- M5H/M5C certification of all routes;
- 50/50 REAL continuation-state certification;
- proving full-game exploitability to a formal bound;
- further MCCFR-vs-ISUCT architecture debates already resolved by 06R3;
- optimization of certification compute that does not change play.

Fantasy-as-current-player and asymmetric/Fantasy x Fantasy playable expansion
becomes the next finite milestone after Normal x Normal PLAYABLE DONE; it is not
silently folded into this first exit criterion.

## Current position

`P1 DONE -> P2 DONE -> P3 state/policy/action/runtime wiring -> PLAYABLE DONE`
