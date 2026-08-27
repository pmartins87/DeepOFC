# M5N Normal×Fantasy pilot — runtime diagnosis

Date: 2026-08-27

## Observed run

Workflow run `33089463461`, job `98578043998`, executed the original two-route M5N paired pilot.

- environment setup: PASS;
- M5N mechanics tests: PASS (`5 passed in 1.98s`);
- quantitative two-route pilot: started at `15:44:35Z` and was cancelled at `18:44:39Z`;
- configured job timeout: 180 minutes;
- firewall validation: skipped because the quantitative step did not finish;
- artifact upload: skipped;
- no strategic exception or assertion failure was emitted before cancellation.

## Classification

`RUNTIME_FEASIBILITY_BLOCKED_NOT_STRATEGIC_FAILURE`

The run does not establish a strategic result for either Normal×Fantasy route. It establishes that the frozen 256-iteration candidate + 1024-iteration challenger + 4×128 held-out paired screen over two routes does not fit the current GitHub-hosted CPU budget.

## Decision

Do not simply increase the timeout and repeat the same experiment.

The next gate is a smaller, precommitted runtime calibration that measures candidate materialization, challenger materialization and paired held-out screening separately on one representative 14-card Fantasy route. Only after those phase timings are known may the production pilot budget or implementation be changed.

Any reduced calibration remains `SCREENING_ONLY`; it cannot be substituted for the original strategic budget and cannot certify an M4Z route.

REAL strategic route count remains `0/50`.
