# DeepOFC PLAYABLE P2 candidate result

Date: 2026-09-02

Verdict: **PASS — P2 COMPLETE**

## Authoritative run

- Workflow: `OpenOFC PLAYABLE P2 Normal-Normal candidate`
- Run: [33597399958](https://github.com/pmartins87/DeepOFC/actions/runs/33597399958)
- Source commit: `3d04fe96fa41e2eb2709b01dc7f8c02e709eb163`
- Artifact: `openofc-playable-p2-normal-normal-candidate`
- Artifact ID: `9834102061`
- Artifact archive SHA-256:
  `52d7d9b674f5b5566baa8fe36fe89dd46c8caaffbf94fa00e57e905531edc7d1`
- Artifact expiry reported by GitHub: 2026-12-01
- Durable repository copy:
  `artifacts/playable_p2_normal_normal_candidate_20260902/`
- Manifest SHA-256:
  `f10c079a61ba08832cfc334afb9c055e023dfc9c23a24140d02b2f7bd8413898`

All four jobs passed: mechanics, B0 training, B1 training and aggregate.

## Frozen routes

| Route | Model SHA-256 | Snapshot SHA-256 | Route SHA-256 | Compressed-file SHA-256 |
|---|---|---|---|---|
| `B0:P0F0:P1F0` | `9cc5d4f09387bee64ea18e91677653e164e878c2153c2f12b232f777ca202f71` | `c6f3f212189e03232345f7ae5dcf30ed0a89e00aa1928a6451d6aab23dcfc92d` | `5f8600bc035197f00de68969c8e0f025a10f1094888999f134f83586f8aa98e1` | `8ecf7a2dd6455e3022fab3e4c26100f5cbbd48508acd1fdebf694a8b30db714a` |
| `B1:P0F0:P1F0` | `5b65fc728c90c65cf17b4462140ea843d80085166e738cb0204460200d337779` | `31f745f80b9141f7e0dc41905ca57746a259e420ccee2314eb255a1b54fc7302` | `4d8d53adf077c0fe4759a7ed876261542adb60983f278bb3cd4de535eed27f0d` | `d47f45f09d266f295a8d62ca137ace58e1e26c2383c3484c978143b3d8cf9eac` |

Both routes used the frozen 4,096-iteration configuration, zero continuation
vector and explicit `MUTUAL_AUTO_SCOOP_NET_ZERO_INFERENCE` policy. The artifact
retains `PLAYABLE_CANDIDATE_NOT_FORMALLY_CERTIFIED` authority and certifies zero
REAL Bellman routes.

## Reproducibility

The first run `33596584411` trained and uploaded both routes successfully but
its aggregate job lacked the repository's NumPy dependency. After adding the
dependency to that job, run `33597399958` repeated both 4,096-iteration
trainings.

The repeated B0 and B1 model SHA-256 and snapshot SHA-256 values were identical
to the first run. Route hashes changed as intended because each route binds its
source commit. This is evidence of deterministic training and correct source
identity binding.

The final ZIP was downloaded independently. Its archive digest matched GitHub,
both route loaders passed, and rebuilding the manifest from the two compressed
routes reproduced the stored manifest byte-for-byte at the logical payload
level.

Because the Actions artifact has a retention deadline, its two immutable route
files and manifest were also committed to the research branch. Their compressed
file hashes match the manifest, so the candidate remains available after the
Actions artifact expires.

## Decision

P2 is closed. No additional solver-family comparison or formal-certification
gate may reopen it without a concrete legality, scoring, information-firewall
or measured strategic failure.

The critical path moves to P3: canonical observation -> policy key/legal action
set -> deterministic action -> runtime drag/verification in recorded shadow
replay, followed by one controlled Normal x Normal hand.
