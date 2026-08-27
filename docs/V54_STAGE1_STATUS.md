# v5.4 Stage 1 — continuity contract and generic Fantasy model

Status: reference implementation complete; native OpenHoldem port still pending.

This stage exists because the v5.3 field failure showed that the runtime could preserve stale canonical lineage indefinitely after a changed scrape was rejected. It also exposed misleading count-bound Fantasy terminology.

Delivered in this stage:

- never-terminal continuity supervisor (`deepofc/runtime_continuity.py`);
- regression coverage for changed/rejected scrapes and reacquisition;
- bootstrap semantics for valid current-screen normal candidates at any round;
- one generic Fantasy runtime mode with card count carried as 14/15/16/17 data;
- explicit current-screen-authority rule over stale process lineage;
- explicit separation between liveness and click safety;
- naming contract preventing new generic `Fantasy15` APIs.

Not claimed by this stage:

- the current Python/OpenHoldem normal reconstructor is not yet self-contained for every partially arranged mid-hand restart;
- the native OpenHoldem `kBlocked` path has not yet been removed;
- native Fantasy current-source detection is not yet wired to runtime authority;
- no new field build is authorized.

Next stage:

1. port the continuity supervisor semantics into the native OpenHoldem controller;
2. replace permanent `Block()` transitions with recoverable fault/reacquire behavior;
3. add a current-screen bootstrap/reconstruction path for normal mid-hand states;
4. wire generic Fantasy 14–17 detection/solver/executor naming and authority;
5. replay the v5.3 failure sequence offline before producing another Windows artifact.
