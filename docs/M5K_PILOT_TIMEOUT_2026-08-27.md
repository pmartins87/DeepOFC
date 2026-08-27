# M5K Normal/Fantasy pilot — timeout record

Status: `CANCELLED_BY_WORKFLOW_TIMEOUT / NO_STRATEGIC_RESULT / SUPERSEDED_BY_M5N`

- GitHub Actions run: `33086327523`
- workflow timeout: `120` minutes
- mechanics/firewall precheck: `23 passed`
- pilot computation started successfully and was terminated at the 120-minute job limit
- no pilot artifact was emitted
- no strategic PASS/FAIL can be inferred from the cancellation

The job log shows `The operation was canceled` at approximately two hours after the pilot step began, matching the workflow `timeout-minutes: 120`. There is no exception or strategic assertion failure before cancellation.

M5N retains the same Normal/Fantasy screening purpose while adding paired per-deal signed differences and explicit uncertainty, and its workflow has a 180-minute limit. To avoid spending compute on a statistically weaker duplicate experiment, M5K is not rerun unless M5N later demonstrates that a distinct M5K result is required for diagnosis.

This timeout changes no authority. REAL route count remains `0/50`.
