# OFC external solver audit — 2026-08-27

Status: **research evidence only — no external component promoted**  
Target: KKPoker-style **heads-up Pineapple OFC Joker Ultimate**, two physical Jokers, exact 14/15/16/17 Fantasy continuation state.  
Frozen internal comparison baseline: `DeepOFC@c3430819d6cb22c8ad823791a35374d56a88a32a`.  
Strategic certification count remains **REAL = 0/50**.

This audit follows `docs/EXTERNAL_SOLVER_RESEARCH_POLICY.md`. A project is compared at an exact commit, never at a moving branch. Sophistication, training volume, or self-reported win rate is not promotion evidence by itself.

## Executive decision

The current DeepOFC architecture remains the strategic authority. None of the audited public projects supplies a directly compatible, independently validated, low-exploitability certificate for the exact HU Joker Ultimate target.

The external review nevertheless found several valuable **component candidates**:

1. deterministic benchmark/scenario manifests and observer-facing hidden-state samplers (`Saholy99/ofcp-engine`);
2. phase-specific hybrid dispatch — exact/bounded late search, search where it pays, learned/fast policies elsewhere (`Saholy99/ofcp-engine`, `StiopaPopa/ananas_final`);
3. fast C++ evaluator/search kernels as **shadow parity implementations**, never as rule authority until cross-validated (`ainaosyusi/ofc-pineapple-ai`, `neery1218/OFCSolver`);
4. Fantasy branch-and-bound as a speed candidate, provided the objective is changed from self-royalty/stay-bonus to the target strategic continuation payoff (`ainaosyusi/ofc-pineapple-ai`);
5. ISMCTS/determinization and learned rollout ideas as experimental search baselines (`xeond8/OFC-Poker-Agents`, Stanford CS224R 2025), but only after target-rule and information-set validation;
6. evaluator/invariant testing discipline, especially the ACE=0 postmortem (`ainaosyusi/ofc-pineapple-ai`).

No architecture migration is authorized by this audit alone.

---

## 1. Pinned sources

| Source | Pinned commit | Primary relevance | Current classification |
|---|---|---|---|
| `ainaosyusi/ofc-pineapple-ai` | `20fcbdebe0cdce3ac06e5ede639b8f78c177ceaa` | C++ engine/evaluator, 2 Jokers, Ultimate Fantasy, 3-max RL, Fantasy B&B | **COMPLEMENTARY / BETTER_CANDIDATE for selected engineering pieces** |
| `yuanzd123/OFC-Pineapple-Solver` | `d3a0c8e0efdc7a86688f3a79b016a122f08b5e93` | current-action Monte Carlo | **COMPLEMENTARY heuristic baseline** |
| `JoshBean1/OFCPoker-Solver` | `1fa00ca0372769b56e0fda3932782ca0b4f1ffce` | MCTS architecture | **RULE_INCOMPATIBLE tree; complementary concept** |
| `Saholy99/ofcp-engine` | `b8e5e2e7c4db5f096bcac7c83b812c9a8d3f542d` | deterministic HU Pineapple engine, MC, bounded search, benchmark manifests | **COMPLEMENTARY / BETTER_CANDIDATE for test/search engineering** |
| `StiopaPopa/ananas_final` | `68df069fd5a7c98e9014d5d27da5f2da8ff3cd85` | 2-player hybrid imitation + PPO + late search | **COMPLEMENTARY architecture idea** |
| `neery1218/OFCSolver` | `0b34b328ee312c7d7b7edba500c36b33266a168c` | C++ Monte Carlo, fast evaluator, multicore | **COMPLEMENTARY throughput; strategic model unsafe as authority** |
| `AKerr94/OFCP-AI` | `bc1aa88e76a606e492f90e8abce2bd8adcace640` | historical MCTS/MC + evaluator regression history | **COMPLEMENTARY historical evidence** |
| `mbkuang/OFC-Solver` | `0bd7a15cb8ea38c60a8c2a122d6ed846ac98c6cd` | claims optimal OFC solutions | **INCONCLUSIVE** — source evidence too weak so far |
| `DexGroves/rl-ofc` | `ccc944df92b8f6899d42c1644d0a3ec178a8cf9f` | A3C/RL environment | **RULE_INCOMPATIBLE (classic one-card OFC)** |
| `jarryxiao/deep-rl-ofc-poker` | `e010ffda7e96fbfc5406be53025bf8df52e43afb` | fork/extension of Dex RL, human-vs-CPU | **RULE_INCOMPATIBLE (classic one-card OFC)** |
| `u03013112/OpenFaceChinesePokerDQN` | `8ced91af8196de547f4c8592a7ae71a96c93fb4e` | Double-DQN shell + browser environment | **INCONCLUSIVE / low-evidence** |
| `xeond8/OFC-Poker-Agents` | `971faf5f794a3b6a0d7aadb0335f0af1fdf41b89` | Pineapple MCTS, ISMCTS, DQN, heuristic SFL, CV | **COMPLEMENTARY; high-value ISMCTS experiment candidate** |
| Stanford CS221 poster, *Building a Pineapple AI* (2018) | public poster | oracle/MC/adversarial completion | **COMPLEMENTARY search evidence** |
| Stanford CS224R, *Advancing Multi-Agent Reasoning in Open-Face Chinese Poker* (2025) | public paper | MCTS+CEM+RAVE+CFR rollout, PPO/DQN comparisons | **COMPLEMENTARY algorithms; RULE_INCOMPATIBLE game** |

The audit should be extended when a new credible implementation or paper is found; these entries are not a closed universe.

---

## 2. Target rule contract versus external rules

Legend: `MATCH`, `MISMATCH`, `PARTIAL`, `UNKNOWN`.

| Rule dimension | DeepOFC target | ainaosyusi | yuanzd123 | JoshBean1 | Saholy99 | Stiopa/Ananas | neery1218 | xeond8 |
|---|---|---|---|---|---|---|---|---|
| players | native HU | core can 2; published RL env hardcodes 3 | HU-shaped | appears HU/classic | native HU | 2-player | variable opponent vector/HU usable | native 2-player |
| deck | 54 | 54 | 52 | 52-classic | 52 | not proven Joker-capable | 52 | 52 |
| Jokers | 2 physical | 2 | none | no target evidence | none | no target evidence | none | none |
| Joker semantics | KKPoker row-local substitution | wildcard evaluator; exact parity not yet proven | N/A | N/A | N/A | UNKNOWN | N/A | N/A |
| opening | receive 5, place all 5 jointly | compatible game semantics | compatible | broadly compatible | compatible | compatible | compatible Pineapple intent | **restricted heuristic starter set** |
| later street | receive 3, place 2, private discard 1 | compatible | compatible | **one card then place** | compatible | compatible | compatible Pineapple | compatible |
| discard visibility | owner-private; public placements signal | intended hidden | model-dependent | no Pineapple discard | hidden | likely hidden; needs source gate | known dead cards accepted | `visible_deck()` intentionally hides opponent dump |
| action order | HU nondealer first, dealer second | 3-max Python modulo-3; core configurable | simplified | classic implementation-specific | non-button first | needs exact audit | solver receives state rather than full game order | alternating first/second |
| scoring | zero-sum row ±1, scoop ±3, royalty diff | broadly standard | broadly standard | variant-dependent | broadly standard | needs exact audit | own-vs-opponent completed hand scoring | broadly standard |
| royalties | target KKPoker tables | close; parity vector required | standard/no Joker | variant-dependent | standard/no Joker | UNKNOWN exact table | standard/no Joker | standard/no Joker; FL bonus mixed into royalty function |
| foul | exact row ordering + zero-sum payoff | present | present | present | present | present | present | present |
| Fantasy entry | QQ=14, KK=15, AA=16, trips=17 | **MATCH** | fixed/standard | separate solver, incompatible variant | fixed 14 | supported but exact mapping UNKNOWN | has Fantasy solver; exact Ultimate mapping absent | encoded as heuristic bonus rather than target continuation state |
| re-Fantasy | top trips OR bottom quads+ | appears MATCH | **MISMATCH** standard/fixed conditions | MISMATCH/UNKNOWN | **MISMATCH** includes middle FH+ | UNKNOWN | UNKNOWN | no exact target state machine |
| Ultimate card retention | keep current 14/15/16/17 after valid re-Fantasy | likely compatible | absent | absent | absent | UNKNOWN | absent | absent |
| Fantasy strategic value | explicit next-state continuation `V[next]` | own royalty + fixed stay bonus in Fantasy solver | fixed bonus heuristic | heuristic/search | fixed-FL heuristics | PPO/hybrid | standalone Fantasy completion | heuristic bonus/search |
| hidden information model | explicit HU infosets, own discards remembered, opponent packet/discards hidden | 3-max obs; published env not HU | local MC simplification | MCTS state depends on classic rules | explicit observer sampler | observation-driven | MC samples completion with approximation issues | ISMCTS key excludes dumps; determinization needs deeper validation |
| unknown cards | exact chance law / sampled deal plans without replacement | environment deck/chance | sampled remaining 52 | chance nodes | observer sampler | env-dependent | **separate hero/opponent samples can overlap** | determinizes by shuffling visible deck |
| native HU strategic training | yes | **NO in published Python RL env** despite C++ core supporting 2 | no global training | no target Pineapple | engine/search yes | yes | MC action evaluation | yes search |
| OpenHoldem runtime | separate live integration track | none | Android/ADB ideas, not OH | none | none | none | server/CLI | CV prototype, not OH |

### Critical HU conclusion for `ainaosyusi`

The distinction is concrete: the C++ `GameEngine` supports two-player construction/showdown paths, while `src/python/ofc_3max_env.py` hardcodes three agents, three-way observations, a three-way position representation, and modulo-3 button rotation. Therefore its trained 3-max policy must **not** be treated as a HU policy by deleting one seat. A dedicated HU environment would require a fresh information-set, turn-order, reward, opponent-mixture and validation audit.

---

## 3. Project dossiers

### 3.1 `ainaosyusi/ofc-pineapple-ai`

**Strongest transferable assets**

- C++17 engine/evaluator for a 54-card two-Joker game;
- pybind11 boundary and fast environment execution;
- exhaustive/branch-and-bound Fantasy placement machinery;
- PettingZoo/MaskablePPO/self-play operational experience;
- unusually valuable postmortem discipline after the V1 failure;
- broad evaluator regression tests in V2.

**Do not transfer directly**

- the trained 3-max policy;
- 3-max observation/position encoding;
- fixed Fantasy stay bonus as strategic value;
- heuristic MCTS expected-value constants;
- any Joker behavior until cross-engine parity is proven against KKPoker row-local semantics.

**Special Joker concern:** the external evaluator is a wildcard evaluator, whereas our target explicitly permits row-local substitution identities. A cross-product corpus must test one/two Joker hands, duplicate represented identities across rows, straight boundaries, top-row substitutions, royalties, foul interactions and tie-breaking.

### 3.2 `yuanzd123/OFC-Pineapple-Solver`

Useful as a transparent local Monte Carlo baseline: enumerate legal current moves, sample future cards and estimate terminal quality. The future is filled greedily rather than played by a strategic sequential policy. It has no Jokers and uses fixed/standard Fantasy assumptions. It can reject very poor current-action heuristics, but it is not a global solver or exploitability authority.

### 3.3 `JoshBean1/OFCPoker-Solver`

The MCTS split between decision nodes and chance nodes is a useful software pattern. The underlying game proceeds with one card after the opening and therefore has a different tree, information structure and branching factor. Copying the tree or statistics would be wrong. Only abstract MCTS engineering ideas qualify for experiments.

### 3.4 `Saholy99/ofcp-engine`

This is the strongest audited source for **engineering methodology** close to our target:

- native HU Pineapple;
- deterministic seeds and reproducible manifests;
- explicit observer-facing sampling of hidden state;
- exact final-draw search when budget permits;
- bounded late search with diagnostics/fallback;
- early candidate pruning with explainable reasons;
- policy composition by game phase.

Its rules still differ materially: 52-card deck, no Jokers, fixed 14-card Fantasy, and re-Fantasy conditions that include middle full-house-or-better. Its early pruning is heuristic and therefore can eliminate the true best action. The correct transfer is the **harness/dispatcher/search-budget pattern**, followed by A/B missed-best-action tests, not the rules or policy values.

### 3.5 `StiopaPopa/ananas_final`

A compact hybrid agent explicitly dispatches by phase:

- opening: imitation model;
- ordinary play: MaskablePPO;
- last street: search;
- Fantasy: PPO path.

This reinforces the hypothesis that one algorithm need not own all phases. Evidence is too small and rule documentation too weak to promote any actual policy. The architecture is a candidate for controlled dispatch experiments only.

### 3.6 `neery1218/OFCSolver`

The C++ implementation is useful for throughput ideas and multicore Monte Carlo. Its strategic simulation has a serious modeling limitation: it samples future hero cards, constructs an optimally completed hero hand, then independently samples opponent cards and optimally completes the opponent. The `Deck::select` method does not consume cards, so independently sampled hero/opponent futures can overlap physically. This violates a joint without-replacement world model. Treat the code as a performance/reference source, not an EV authority.

### 3.7 `AKerr94/OFCP-AI`

Historical project with MCTS/Monte Carlo, dissertation/report and unit tests. Its latest pinned commit is itself an evaluator repair: unordered five-high straights had been misclassified as high card. This is a second independent example, after ACE=0, showing why evaluator semantics must be gated before costly policy learning.

### 3.8 `DexGroves/rl-ofc` and `jarryxiao/deep-rl-ofc-poker`

These are classic one-card OFC environments, not Pineapple. After the five starting cards, eight cards are received one at a time and placed directly. Several files in the later `jarryxiao` project are byte-identical to the older Dex project; the main extension adds human-vs-CPU interaction. They can inform historical RL state encoding but are rule-incompatible as target environments.

There is also a suspicious deck slicing pattern (`deck[0:5]` and `deck[6:11]`) that skips index 5 in the initial assignment. This is another reason to use them only as historical references unless independently rebuilt and tested.

### 3.9 `u03013112/OpenFaceChinesePokerDQN`

The repository contains a Double-DQN learner and a WebSocket bridge. The actual environment/game semantics are delegated to a browser client rather than materialized in the Python repository. Python exposes only a 45-dimensional observation, 15 actions, reward/done and legal-action query from the remote browser. Without the exact browser source/rule contract, strategic compatibility cannot be established. Classification remains **INCONCLUSIVE**.

### 3.10 `xeond8/OFC-Poker-Agents`

This recent repository is strategically interesting because it includes MCTS, **ISMCTS**, DQN, minimax, heuristic “SimpleFantasyLike” search and a computer-vision prototype.

Positive ideas:

- an information-set key for ISMCTS that excludes discard piles;
- determinization by resampling/shuffling unseen deck state;
- direct comparison of MCTS/ISMCTS/DQN/heuristic combinations under a fixed 12-second move budget;
- reported 200-game random-opponent benchmark where ISMCTS+SFL is strongest among its listed agents.

Important caveats:

- 52 cards, no target Jokers/Ultimate state;
- opening actions are deliberately restricted by `valid_starters`, so the system does **not** preserve our full 232-action opening space;
- Fantasy value is mixed into heuristic royalty scoring rather than represented by our exact continuation state;
- headline evaluation is only 200 games against a random agent;
- the ISMCTS implementation must be checked for determinization consistency, legal-action availability under determinizations, opponent strategy, tree-policy semantics and reproducibility before strategic use;
- CV code is a prototype and not an OpenHoldem integration.

The highest-value experiment here is an **isolated target-rule ISMCTS baseline** built over our own engine/information-state contract, not importing the external environment.

---

## 4. ACE=0 / 250M-step failure postmortem

The V1 `ainaosyusi` campaign is the clearest warning in the audit. More than 250M training steps were invalidated because the evaluator's compact rank encoding used Ace as `0`, and that representation leaked into strength ordering so that cases such as `AA < 22` became possible.

### Why this is more serious than one evaluator bug

An RL run can be perfectly reproducible and still learn the wrong game. Once the environment emits systematically incorrect terminal values, more samples reinforce the defect. A larger model and longer training can make the resulting policy more confidently wrong.

The postmortem also records adjacent hazards:

- reward shaping strong enough to dominate the native foul penalty;
- semantic aliasing of action IDs between the opening and later streets;
- weak objective evaluation foundations;
- small self-play opponent pools;
- fixed-seat/position overfitting risk.

### Preventive control added to DeepOFC

The research branch now contains `tools/openofc_solver/test_semantic_invariant_firewall.py` and workflow `.github/workflows/openofc-external-research-semantic-invariants.yml`.

GitHub Actions run `33134947365` passed **12/12** invariants. Frozen semantic manifest:

`07722c5b3ee7adc60a9c2ad05290385207c7eb7e2e60ac0ee39de1ed1ad6d3e4`

Artifact ZIP digest:

`80a3fc4d98cd817e3bc78cdf412de5bddd481fe05b62bf295f2a6a799dced122`

The gate covers Ace/pair ordering, category ordering, wheel/Broadway, Joker semantics, two-Joker royal completion, Fantasy 14/15/16/17, target re-Fantasy semantics, HU antisymmetry, opening/Pineapple action semantics and hidden-information non-leakage.

This gate is intentionally labeled `SEMANTIC_RULE_GATE_NOT_STRATEGIC_CERTIFICATION`: passing it prevents known classes of catastrophic training corruption; it does not prove a policy is strong.

---

## 5. Required component matrix

| componente | nosso método | projeto externo | diferença de regras | vantagem teórica | risco | teste necessário | decisão |
|---|---|---|---|---|---|---|---|
| representação do estado | native HU extensive-form infosets + 50 cross-hand continuation states; own private discards remembered, opponent hidden | Saholy observer state; aina 3-max PettingZoo; xeond8 ISMCTS info key | aina is 3-max; Saholy/xeond8 no Jokers/Ultimate | observer sampler and explicit determinization can make search modular | hidden leakage or under-specified history/perfect recall | paired worlds differing only in opponent-hidden variables; perfect-recall property tests | **KEEP ours; borrow observer-sampler harness** |
| evaluator | exact 3/5-card evaluator, Ace=14, target foul/royalties | aina C++; neery fast C++; Deuces/Treys projects | external Joker/no-Joker and top-row details vary | large C++ speedup possible | tiny semantic drift corrupts every solver/training result | exhaustive/random differential parity corpus, especially Ace/Joker/foul/ties | **SHADOW C++ candidate only** |
| Joker | 2 physical Jokers, KKPoker row-local substitution, strongest legal non-foul resolution | aina wildcard evaluator | exact substitution/tie semantics not yet proved identical | C++ wildcard routines may be faster | wrong cross-row substitution, kicker or tie behavior | one/two-Joker cross-product differential corpus | **INCONCLUSIVE until parity** |
| scoring | exact HU zero-sum row/scoop/royalty/foul | most projects broadly standard | royalties/Fantasy bonuses differ; some blend Fantasy bonus into score | mature external evaluators useful for parity | reward shaping or FL bonus changes game objective | antisymmetry + golden KKPoker board corpus | **KEEP ours** |
| geração de ações | full legal action generation | aina/yuanzd/Saholy full-ish; xeond8 restricted opening | xeond8 starter pruning is heuristic | pruning can reduce branching dramatically | removes optimal action | exact action-set identity; missed-best-action rate on exact teachers | **KEEP full set; pruning only experimental** |
| abertura | all 232 legal placements, no abstraction | aina; Saholy; Stiopa imitation; xeond8 restricted starters | external learned/heuristic openings may omit target actions | opening-specific model may save substantial compute | early policy error compounds through hand | exact/BR labels on tractable corpora + downstream EV A/B | **phase-specific candidate, no replacement yet** |
| streets Pineapple | receive3/place2/private-discard1, full sequential signalling | aina, yuanzd, Saholy, Stiopa, neery, xeond8 | Josh/Dex/jarry are one-card classic OFC | mature enumeration/search patterns | action aliasing, discard leakage, wrong order | action cardinality/semantics + hidden-discard invariants | **borrow harness ideas only** |
| Fantasy | exact target placement solvers + 14/15/16/17 continuation state; no arbitrary bonus | aina B&B; Saholy fixed14; yuanzd fixed bonus; Stiopa PPO | all but aina differ materially; aina B&B objective still self-focused | B&B may speed exact placement search | optimizing royalties+stay bonus instead of adversarial continuation value | same packet/boards/V, compare chosen action and exact continuation payoff | **aina B&B speed candidate after objective rewrite** |
| estimador de EV | strategic current-hand utility + explicit continuation V; M5R bounded BR machinery | yuanzd MC; neery MC; xeond8 SFL; Stanford oracles | external methods use greedy/perfect-future/fixed bonuses | very fast screening/ranking candidates | optimistic or biased rollouts mistaken for true EV | exact reduced-game bias/RMSE/rank-correlation + policy regret | **use only as screening/control variates** |
| rollout | outcome-sampling MCCFR / exact terminal evaluator; learned-response only screening | aina random/heuristic; Saholy heuristic; Stanford CFR rollouts | external game/rules differ | learned rollouts can lower MCTS variance | rollout bias drives search policy | common-root search A/B at equal terminal work | **candidate after target-rule rebuild** |
| MCTS | no canonical production MCTS authority | Josh MCTS; xeond8 MCTS/ISMCTS; Stanford MCTS+CEM+RAVE+CFR | Josh/Stanford game mismatch; xeond8 52-card no Ultimate | adaptive compute allocation to promising branches | no exploitability upper bound; determinization strategy fusion; expensive | reduced-game exact BR/regret and equal-work comparisons | **experimental baseline, not certifier** |
| Monte Carlo | used where sampling is explicitly approximate/evaluation; certification authority kept separate | yuanzd, Saholy, neery | external continuation laws/objectives differ | cheap scalable action ranking | greedy/perfect-future bias; non-joint sampling | exact-world joint chance parity; calibration/bias curves | **complementary only** |
| RL/self-play | not current certification authority; current strategic core MCCFR/current-V solvers | aina MaskablePPO/self-play; Stiopa PPO; Dex/jarry A3C; u030 DQN | most environments wrong variant/player count | amortized low-latency policy; can learn nonlinear heuristics | semantic bugs, reward hacking, nonstationarity, exploitability unknown | semantic firewall first; diverse opponents; heldout exploiters/exact reduced games | **defer heavy training** |
| reward | native zero-sum points + exact continuation state value | aina V1 shaping; Stiopa/PPO env; Stanford shaped reward | shaping often changes objective | shaping can improve sample efficiency | optimizes proxy rather than poker value | prove potential-based invariance or A/B against native objective | **native reward remains authority** |
| opponent information | explicit imperfect-information infosets; own discard private memory; no opponent packet/discards | Saholy observer sampler; xeond8 ISMCTS; aina 3-max obs | external visibility contracts differ | explicit determinizations can aid search | information leakage or strategy fusion | hidden-world equivalence tests and public-history posterior tests | **KEEP ours; build target observer sampler candidate** |
| HU | native and strategically explicit | Saholy/Stiopa/xeond8 native HU; aina core can2 but RL env=3 | 3max→HU is not policy-equivalent | direct HU search references exist | accidentally import 3max position/reward/opponent mixture | dedicated HU env golden trajectories | **ours remains authority** |
| performance | Python strategic stack + M5R rigorous pruning/budget control; exact reduced authorities | C++ aina/neery; bounded search Saholy | rules/objectives vary | large wall-clock gains likely from low-level kernels and phase dispatch | speed by approximation can weaken guarantees | equal semantic workload, cold/warm timing, memory, exact result parity | **high-priority engineering A/B** |
| determinismo | fixed seeds, SHA-bound snapshots/manifests/checkpoints | Saholy strong deterministic manifests; many RL/search repos use global RNG | external reproducibility varies | easier regression and scientific comparison | stochastic drift hides defects | replay identity across machines/seeds where possible | **adopt Saholy-style manifest discipline more broadly** |
| testes | extensive exact/reduced strategic tests + new semantic firewall | aina V2 regression suite; AKerr evaluator fix; Saholy scenario corpus | rule vectors differ | external failures reveal missing invariant classes | copying wrong expected values | translate each external failure into target-rule invariant | **EXPAND ours continuously** |
| integração runtime/OpenHoldem | separate OH scraper/state bridge/autoplayer track | yuanzd Android/ADB; xeond8 CV prototype | UI/platform completely different | recognition/recovery ideas may transfer | strategic code contaminated by UI assumptions | recorded-frame parity, unknown-card recovery, shadow mode | **separate runtime research only** |

---

## 6. What is actually better, worse, equivalent, complementary

### Better candidate than our current implementation — **only at component level**

- `Saholy99` reproducible benchmark/manifest discipline for search experiments.
- `Saholy99` bounded late-search diagnostics/fallback engineering.
- C++ low-level evaluator/search throughput from `ainaosyusi` or `neery1218`, **if and only if** exact parity is established.
- `ainaosyusi` exhaustive Fantasy branch-and-bound as a possible performance kernel after changing the objective to our continuation-aware payoff.

### Roughly equivalent idea, different implementation

- legal Pineapple action enumeration in several Pineapple repos;
- standard row/scoop/royalty scoring surface where no Joker/Fantasy differences intervene;
- hidden-discard sampling concept in Saholy/xeond8 versus our explicit imperfect-information model.

### Worse for the target strategic objective

- greedy future filling as EV (`yuanzd123`);
- independently sampled, potentially overlapping hero/opponent futures (`neery1218`);
- fixed Fantasy bonuses standing in for continuation value;
- random-opponent win rate as primary quality metric;
- heuristic opening action elimination without a missed-optimum bound.

### Complementary

- MCTS/ISMCTS as bounded decision-time search;
- PPO/DQN as fast policy proposals/rollout policies;
- imitation learning for opening proposals;
- CV/ADB recognition prototypes for the separate runtime track;
- CEM/RAVE/CFR-rollout search ideas from academic work.

### Rule-incompatible

- classic one-card OFC projects (`JoshBean1` tree, `DexGroves`, `jarryxiao`);
- all no-Joker/fixed-Fantasy engines as direct target replacements;
- published `ainaosyusi` 3-max RL policy as a HU policy.

### Still inconclusive

- exact Joker semantic parity with `ainaosyusi`;
- `mbkuang/OFC-Solver` “optimal” claim;
- browser-defined game semantics in `u03013112`;
- exact target-rule details in `StiopaPopa/ananas_final` beyond high-level Pineapple/HU behavior.

---

## 7. Ranked experiment backlog

### E1 — evaluator differential parity shadow

Build an external-style fast evaluator adapter behind a test-only interface. Feed the same target board corpus to it and `engine.py`; demand exact agreement on category, tie order, royalties, foul, Joker resolution, Fantasy qualification and HU score. **Any mismatch blocks performance claims.**

### E2 — target-rule observer sampler

Borrow Saholy/ISMCTS architecture, not its rules: construct a sampler that accepts one DeepOFC information state and samples only worlds consistent with public history, own cards/discards and target deck law. Validate by exact enumeration on reduced games.

### E3 — phase-specific late exact search

Add a shadow dispatcher that invokes exact/bounded search only when the remaining tree fits a declared terminal-work budget. Compare with baseline on exact R4/R3 authorities and measure wall time, nodes and policy regret. This is the lowest-risk external architectural import.

### E4 — Fantasy branch-and-bound shadow

Port only the pruning/order ideas from `ainaosyusi` while keeping DeepOFC's objective: current HU payoff + exact `V[next_state]`. Compare action identity/value against existing exact Fantasy authorities for 14/15/16/17 and Joker stress corpora.

### E5 — target ISMCTS baseline

Implement ISMCTS on our engine/observer sampler with deterministic seeds. Compare MCTS, ISMCTS, MCCFR-derived fixed policy and learned-response screening at equal terminal-work budget on reduced games. Never promote from random-opponent APG alone.

### E6 — learned rollout / proposal policy

Only after E1–E5 and the semantic gate are stable, train a small policy solely as a rollout/proposal accelerator. The search/certification layer remains capable of rejecting it. Heavy end-to-end self-play remains later.

---

## 8. Promotion gates

An external candidate can be promoted only if:

1. exact target rules are SHA-bound;
2. semantic invariant firewall passes;
3. no hidden-information leakage is found;
4. candidate and baseline are evaluated on identical legal states/chance seeds where valid;
5. quality metric is native strategic value/regret/exploitability evidence, not only heuristic score or random-opponent wins;
6. wall-clock gain is measured separately from strategic approximation loss;
7. reduced-game exact authorities show no unbounded regression;
8. if approximate, the component remains below the correct certification firewall;
9. OpenHoldem/runtime change, if any, passes its own recorded-frame/shadow/live-safety gate;
10. the old implementation remains available until the replacement is proved and reviewed.

## Final audit decision at this checkpoint

**Preserve the current DeepOFC strategic architecture.** The external ecosystem has supplied concrete ways to improve performance engineering, search dispatch, benchmarking and pre-training safety, but has not supplied a demonstrably superior drop-in HU Joker Ultimate solver.

The highest-value immediate work is therefore:

`current DeepOFC + target-rule semantic firewall + external engineering candidates + isolated A/B tests`

and explicitly not:

`replace DeepOFC with any public repository`.
