# OpenOFC external research — 05C-Q1 reproducibility result

Date: 2026-08-28
Branch: `research/external-ofc-solver-audit-20260827`
Run: `33141974295`
Head: `6749e39f509954364e1a3ec85f328aaf14e40b3c`
Status: **SUCCESS / REPRODUCIBILITY DIAGNOSTIC ONLY**

## Frozen matrix

The Q1 matrix used the same six physical worlds and exploration constant `1.0` for every cell.

Budgets: 1,000 / 5,000 / 20,000 iterations.
Seeds: 2026082841 / 2026082843 / 2026082847 / 2026082849.

## Root-action stability

All **12/12** cells selected the same P0 R3 action:

`discard 8h; 7c -> bottom; 8c -> bottom`.

That is also the action selected by Q0. Root visit concentration increased with budget:

| Budget | Same action / seeds | Mean selected-root visit share |
|---:|---:|---:|
| 1,000 | 4/4 | 98.0% |
| 5,000 | 4/4 | 99.6% |
| 20,000 | 4/4 | 99.9% |

## Tree coverage and trajectory statistics

| Budget | Infosets | Mean fully-covered fraction | Mean terminal P0 utility | Cross-seed σ |
|---:|---:|---:|---:|---:|
| 1,000 | 704–714 (mean 709.5) | 19.20% | 26.6080 | 0.04999 |
| 5,000 | 949 | 80.40% | 27.1854 | 0.00000 |
| 20,000 | 949 | 80.40% | 27.79635 | 0.00000 |

The search therefore stabilized its root decision very early on this tiny support, while the on-search terminal mean continued to rise materially with budget. That rise must **not** be read as equilibrium-value improvement: UCT changes both players' exploratory behavior over time, and the trajectory mean is not an exploitability estimator.

The identical 5k/20k aggregate statistics across the four RNG seeds are a useful warning rather than extra authority. Once this small support/tree enters a highly concentrated regime, root-action reproducibility alone stops being a discriminating quality metric. The next experiment needs an independent strategic algorithm, not more seeds of the same search.

## Evidence

- workflow: `OpenOFC external two-street infoset Q1`
- run: `33141974295`
- job: `98754590805`
- Q0 revalidation: **3 passed**
- artifact: `openofc-external-two-street-05c-q1`
- artifact ID: `9674320715`
- artifact ZIP SHA256: `81b384b1f16490e70941c292d2c2ec1fcad24051870ff206c0e1d9045aab8d72`
- manifest SHA256: `42cbf0fde6ae431d8fa25d229d1566767fd85770ad88405fd25ff5e1eaabb807`

## Decision

05C is mechanically stable enough to stop spending budget on same-algorithm reproducibility. The research frontier moves to **05D**, an independent CFR-family comparator on exactly the same reduced game.

Q1 creates no strategic certificate. REAL routes remain **0/50**.
