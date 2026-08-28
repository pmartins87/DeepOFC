# OFC external research — Phase 4 / 05A result — 2026-08-28

Status: **research/shadow evidence only**  
Frozen strategic baseline: `DeepOFC@c3430819d6cb22c8ad823791a35374d56a88a32a`  
Research branch experiment head: `813f9512b04062d6049016e4d5c871fb06eeab19`  
Strategic route certificates: **REAL = 0/50**.

## EXT-ISMCTS-05A-R4-REDUCED

Purpose: test the first target-rule HU information-set search primitive before attempting a deeper ISMCTS tree.

External architecture reference only:

- `xeond8/OFC-Poker-Agents@971faf5f794a3b6a0d7aadb0335f0af1fdf41b89`;
- `bot/ismcts.py`.

DeepOFC implementation:

- `tools/openofc_solver/external_r4_infoset_search.py`;
- `tools/openofc_solver/test_external_r4_infoset_search.py`.

Authority:

`UNIFORM_FINITE_SUPPORT_R4_INFOSET_SEARCH_SCREENING_ONLY`

### Experimental game

A physically coherent P0-first R4 state is frozen. P0 sees its legal information state, while P1's current 3-card packet is hidden. The experiment uses an explicit finite support of 12 possible P1 packets, including single- and dual-Joker worlds.

P0 has six legal root actions. The exact comparator enumerates every root action over all 12 hidden worlds and lets P1 choose its exact final response after observing its own packet and P0's public placement. Therefore the comparator is the exact value of this **finite-support uniform reduced game**, not the exact posterior of the full OFC game.

The candidate search uses one P0 root information-set node shared by all hidden packets, UCB1 root action selection, one sampled hidden packet per iteration, and an exact P1 final response. Hidden packet identity is never part of the P0 root-node key.

### Result

- workflow run: `33140901281`;
- job: `98751314820`;
- result: **SUCCESS**;
- tests: **3 passed**;
- iterations: **50,000**;
- seed: `2026082805`;
- finite-support exact best value: **19.666666666666668**;
- selected action was an exact optimum: **yes**;
- selected empirical value: **19.685435961034546**;
- selected exact value: **19.666666666666668**;
- absolute value error: **0.01876929436787833**;
- manifest SHA256: `47384aade8e8539a9e6f8e0dca4e5aab21e70149b78edbf636daa95b20f113d5`;
- artifact id: `9673888142`;
- artifact name: `openofc-external-r4-infoset-search-05a`;
- artifact ZIP SHA256: `edc20f047f44ff894c387de7c3f7416f2473697725545457728c4083dad2a766`.

Selected canonical action:

```text
{"d":"9d","p":[["As",0],["Qh",1]]}
```

Meaning under the target action codec: discard `9d`, place `As` on row 0 and `Qh` on row 1.

The exact reduced game has four tied optimal root actions at value `19.666666666666668`:

```text
{"d":"9d","p":[["As",0],["Qh",1]]}
{"d":"As","p":[["9d",0],["Qh",1]]}
{"d":"Qh","p":[["9d",0],["As",1]]}
{"d":"Qh","p":[["9d",1],["As",0]]}
```

The other two root actions have exact value `-8.583333333333334`.

### Important diagnostic nuance

The root UCB policy concentrated 49,993 of 50,000 visits on the selected arm. Some other exact-optimal tied arms were visited only 1–3 times after unfavorable early samples. This does **not** invalidate the selected-action result, because the selected arm is independently known to be exact-optimal and its mean converged closely to the enumerated expectation. It does show that this root-only UCB pilot is not a reliable estimator of the full tied optimal-action set.

That observation changes the next experiment design: 05B must validate tree semantics and opponent perspective with explicit information-set nodes, and quality gates should compare the chosen value/action against exact enumeration rather than require accurate estimates for every rarely visited arm.

### Decision

`CONTINUE_TO_FULL_ISMCTS_SHADOW_ONLY`

05A is evidence that the target engine, legal information-state key, hidden-world sampling and root aggregation can support an information-set search experiment without leaking P1's packet into P0's node identity. It is **not** evidence that ISMCTS is better than the current strategic solver, and it is not a certification result.

## Next experiment

`EXT-ISMCTS-05B-R4-TREE` will replace the exact P1 response shortcut with explicit P1 information-set nodes:

1. sample one hidden P1 packet;
2. select P0 root action using only P0 information-set statistics;
3. enter a P1 node keyed by P1's legal information state after P0's public placement;
4. select P1 action from P1's perspective;
5. evaluate exact terminal utility;
6. backpropagate with correct zero-sum perspective;
7. compare the learned root decision against the independently enumerated finite-support exact game.

The purpose is to validate information-set node aggregation and perspective handling before moving to a two-street tree where search depth becomes strategically meaningful.
