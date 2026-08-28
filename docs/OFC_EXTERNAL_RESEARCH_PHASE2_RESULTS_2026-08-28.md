# OFC external research — Phase 2 results — 2026-08-28

Status: **research/shadow evidence only**  
Frozen strategic baseline: `DeepOFC@c3430819d6cb22c8ad823791a35374d56a88a32a`  
Research branch: `research/external-ofc-solver-audit-20260827`  
Strategic route certificates: **REAL = 0/50**

This document preserves the first executable component-level results produced under `docs/OFC_EXTERNAL_COMPONENT_AB_PROTOCOL.md`. None of these experiments is allowed to change Bellman-route certification authority.

## EXT-EVAL-01A — `ainaosyusi` evaluator/Joker vectors

External source:

- repository: `ainaosyusi/ofc-pineapple-ai`;
- pinned commit: `20fcbdebe0cdce3ac06e5ede639b8f78c177ceaa`;
- audited files: `src/cpp/evaluator.hpp`, `tests/test_evaluator_comprehensive.py`, `tests/test_joker.py`.

Internal executable shadow vectors:

- `tools/openofc_solver/test_external_evaluator_parity_vectors.py`.

Result:

- workflow run: `33140106900`;
- job: `98748827944`;
- result: **SUCCESS**;
- tests: **5 passed**;
- experiment manifest SHA256: `1d41c705ac97fcfdaba1acdddc10e08c4b651e19ca3b720c261d9a89b8098d99`;
- artifact id: `9673593185`;
- artifact name: `openofc-external-evaluator-parity-01a`;
- artifact ZIP SHA256: `ae2192efff801abee4cc498a64886b0caff3f29330ab1f029f0a47b3dd67f7ab`;
- authority: `SEMANTIC_PARITY_RESEARCH_ONLY`;
- promotion recommendation: `KEEP_BASELINE`.

### What matched

The target evaluator reproduces the useful published regression classes:

- Ace ordering, including `AA > KK > ... > 22`;
- Ace high-card and kicker ordering;
- made-hand category ordering;
- wheel and Broadway boundaries;
- representative one/two-Joker made hands;
- standard Top/Middle/Bottom royalty vectors.

### Material incompatibility found

The external C++ evaluator gives a Joker a synthetic comparison kicker `15` in a non-straight-flush flush, explicitly above Ace `14`. That is not equivalent to the frozen KKPoker row-local wildcard substitution semantics.

Counterexample frozen as a regression:

- H1: `As 9s 8s 7s JK1`;
- H2: `As Ks Qs 9s 8s`.

Under the target semantics H1 resolves best as `A-K-9-8-7`; H2 is `A-K-Q-9-8`, so **H2 > H1**. The source-level synthetic-15 comparison reverses that order. Therefore the external evaluator cannot be imported wholesale even though many published vectors agree.

Decision: retain DeepOFC evaluator/Joker authority; keep the external tests as regression inspiration only.

---

## EXT-SAMPLER-02A — single shared physical world

External engineering references:

- positive pattern: `Saholy99/ofcp-engine@b8e5e2e7c4db5f096bcac7c83b812c9a8d3f542d`, `src/ofc_solver/sampler.py`;
- negative regression reference: `neery1218/OFCSolver@0b34b328ee312c7d7b7edba500c36b33266a168c`, `solver/src/solver.cc`.

Internal research implementation:

- `tools/openofc_solver/external_research_world_sampler.py`;
- `tools/openofc_solver/test_external_research_world_sampler.py`.

Result:

- workflow run: `33140106963`;
- job: `98748828333`;
- result: **SUCCESS**;
- tests: **5 passed**;
- experiment manifest SHA256: `20d9773b603769e64853a0e16cf6c27be55200f4dc7220ac3930fc620c5e8bce`;
- artifact id: `9673592712`;
- artifact name: `openofc-external-world-sampler-02a`;
- artifact ZIP SHA256: `509e053f6d9eff4896930d9f90df33cf5c2aa240ba337836100cb353a198a677`;
- authority: `UNIFORM_CONDITIONAL_PHYSICAL_WORLD_SAMPLER_SCREENING_ONLY`;
- promotion recommendation: `PROMOTE_SHADOW`.

### What the shadow sampler guarantees

- exactly one shared 54-card physical world;
- every known/hidden/undealt physical card appears exactly once;
- disjoint named hidden zones;
- deterministic replay under the same seed and inputs;
- rejection of duplicate known cards, duplicate zones and oversubscription.

The regression test also models the audited `neery1218` anti-pattern: independently selecting Hero and opponent future cards from the same undepleted Deck can assign the same physical card to both futures. The shadow sampler makes this structurally impossible.

### What the shadow sampler does not guarantee

It is uniform conditional on the explicit known-card set. It is **not** a Bayesian/strategic posterior conditioned on public action history. In OFC, public placements can signal private packets/discards. Therefore this sampler is suitable for controlled MC/MCTS/ISMCTS screening, but cannot become an exact infoset belief authority or certify exploitability.

---

## Updated component decisions

| component | internal authority | external observation | current decision |
|---|---|---|---|
| evaluator rank/category | DeepOFC exact target evaluator | published `ainaosyusi` V2 regression vectors largely agree | **KEEP_BASELINE** |
| Joker comparison | KKPoker row-local wildcard substitution | `ainaosyusi` non-SF flush uses synthetic Joker kicker 15 | **REJECT external rule** |
| pre-training invariants | DeepOFC semantic firewall | external ACE=0 and historical evaluator failures motivate broader gates | **ADOPT methodology** |
| hidden physical-world consistency | DeepOFC joint deal plans | Saholy sampler consumes one shared unseen deck | **ADOPT as shadow pattern** |
| split hero/opponent MC completion | joint physical world required | `neery1218` can overlap sampled future cards | **REJECT** |
| posterior belief | strategic infoset solver required | simple determinization samplers do not condition on signalling | **INCONCLUSIVE / screening only** |

## Next gates

1. classify phase-specific late exact/bounded search against DeepOFC’s existing exact terminal teachers;
2. audit the external Fantasy recursive solver against DeepOFC V1/V2 exact 14–17-card kernels and continuation objective;
3. establish a current Fantasy performance baseline before considering any C++ rewrite;
4. only after those gates, build the target-rule ISMCTS experiment on the shadow physical-world sampler.

No external policy, evaluator, Fantasy objective, MCTS implementation, or RL checkpoint has been promoted to strategic authority.
