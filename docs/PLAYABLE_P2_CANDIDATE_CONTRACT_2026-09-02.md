# DeepOFC PLAYABLE P2 Normal x Normal candidate contract

Date: 2026-09-02

Branch: `research/external-ofc-solver-audit-20260827`

Authority: `PLAYABLE_CANDIDATE_NOT_FORMALLY_CERTIFIED`

## Finite deliverable

P2 produces exactly two immutable deployable route files, one for each button
state, plus one aggregate manifest:

- `B0:P0F0:P1F0`;
- `B1:P0F0:P1F0`;
- a manifest binding both route-file hashes, model hashes, policy-snapshot
  hashes and the source Git commit.

The model is the bounded visible-information action-advantage generalizer
distilled from the selected external-sampling MCCFR architecture. It supplies a
complete policy for any canonical visible Normal x Normal key and its public
legal action set, including states not revisited tabularly during training.

## Frozen training configuration

| Field | Value |
|---|---:|
| MCCFR iterations per button route | 4,096 |
| Evaluation samples | 512 |
| Replay capacity | 100,000 |
| Fit epochs | 4 |
| Model interaction buckets | 65,536 |
| Outcome-sampling epsilon | 0.6 |
| Base seed | 2,026,090,201 |
| Continuation vector | all 50 states = 0 |
| Deterministic action selection | maximum probability, then lexical canonical action key |

The zero continuation vector makes this first artifact a current-hand Normal x
Normal policy. It does not claim that later Fantasy continuation value is
solved. Fantasy-current-player expansion remains the next finite milestone
after P3.

## Simultaneous both-foul edge case

The official [KKPoker game-rules page](https://kkpoker.net/gamerules/) says that
a fouled player is automatically scooped by opposing players, but does not
explicitly define heads-up settlement when both players foul simultaneously.

Therefore:

- the canonical `deepofc.scoring` source remains fail-closed for both-foul;
- this PLAYABLE artifact alone opts into
  `MUTUAL_AUTO_SCOOP_NET_ZERO_INFERENCE`;
- the inference is that equal mutual automatic scoops cancel, neither player
  receives royalties or Fantasy entry, and pairwise net points are zero;
- the policy name is embedded in the objective, configuration and snapshot
  hashes so later source-backed replacement cannot silently change an artifact.

This is an explicit engineering assumption, not a claim that KKPoker has
published the simultaneous-settlement rule.

## Artifact identity and acceptance

Every route contains:

- schema and non-certifying authority;
- source 40-hex Git commit;
- complete training configuration and SHA-256;
- continuation objective and SHA-256;
- complete model weights/optimizer payload and SHA-256;
- immutable policy snapshot and SHA-256;
- training/materialization report and seed identities;
- explicit limitations: formal certification false, production certification
  eligibility false, REAL routes certified zero, Fantasy continuation unsolved.

P2 passes only when:

1. both route jobs complete at the frozen budget;
2. route reload reproduces policy probabilities and deterministic selected
   actions;
3. inner and outer tampering is rejected;
4. the aggregate manifest validates B0 and B1 from one source commit;
5. the bounded mechanics/scoring/regression battery is green.

No new solver-family tournament is authorized inside P2. A concrete legality,
scoring, information-firewall or measured strategic failure may reopen only the
specific affected component.
