# M5N — Normal/Fantasy runtime diagnosis

Date: 2026-08-27

Status: **RUNTIME BOTTLENECK ISOLATED — NOT STRATEGIC EVIDENCE**

## Context

The two-route M5N strategic pilot (`33089463461`) reached its 180-minute workflow timeout without producing an artifact. A later phase-timed F17 calibration (`33114482820`) also reached its 30-minute timeout before a phase result was flushed. The M5N mechanics tests themselves remained green.

Rather than rerunning the same expensive workload, a matrix microprobe isolated exactly one cold M4H one-pass terminal evaluation for F14 and F17.

## Microprobe

Workflow: `33117461944`

Both matrix jobs passed after correcting an instrumentation-only action-ordering bug in the first attempt.

| Fantasy count | one cold exact terminal evaluation | cache state |
| --- | ---: | --- |
| F14 | 1.964799293 s | 0 hits / 1 miss |
| F17 | 66.617573291 s | 0 hits / 1 miss |

The observed F17/F14 ratio is approximately **33.91x** for these deterministic worlds.

Payload identities:

- F14: `abbea5f2f971b23cd0ce58891e751e7ddc7cd81c743e715fd89e304b8b9bf4d3`
- F17: `82ab9d2f59660bbdd381ebc93028124cba1eb96a157e69a2a77fddf37c1ac47b`

## Interpretation

This materially changes the runtime diagnosis. F17 is not merely a slightly larger version of F14. A single cold exact Fantasy terminal solve can be tens of times more expensive. M5B training and M5N screening invoke terminal evaluation many times, so the observed workflow timeouts are consistent with exact terminal frontier work dominating the F17 path.

This microprobe does not prove that every F17 world is 33.91x slower, and it is not strategic evidence. It does prove that a concrete deterministic F17 terminal world has a very large cold exact-evaluation cost relative to its F14 companion under the current implementation.

## Follow-up instrumentation

The F17 phase-timed calibration is now schema `openofc-m5n-normal-fantasy-runtime-calibration-f17-v2` and flushes `start` / `done` markers around candidate materialization, challenger materialization and paired screening. A future timeout will therefore identify the first unfinished phase even if no JSON artifact is emitted.

## Decision

Do not rerun the full F17 strategic pilot unchanged.

The next runtime work is:

1. use the heartbeat calibration to identify which complete M5B/M5N phase dominates;
2. audit M4H one-pass frontier cache keys and reuse opportunities across repeated terminal calls;
3. determine whether expensive F17 work can be decomposed or memoized without changing exact semantics;
4. if an approximation is considered, use only a separately held-out, SHA-bound certified envelope with exact fallback. An approximate terminal model cannot silently replace M4H authority.

## Authority firewall

This diagnosis changes no strategic status. No route is promoted to REAL and the final certification count remains 0/50.
