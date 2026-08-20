# v5.4 field gate

No v5.4 Windows field package may be produced until the native runtime proves the following offline:

1. no scraper/reconstruction error can enter a permanent blocked state;
2. the v5.3 `Hero incoming card identities changed within the same round` sequence reaches `REACQUIRE` and then accepts the current newer round;
3. a fresh process can bootstrap from a current normal mid-hand state rather than waiting for a new hand;
4. a fresh process can bootstrap from active Fantasy with 14, 15, 16, or 17 cards;
5. Fantasy is logged and routed as one generic mode plus `fantasy_card_count`;
6. stale plans are discarded after reacquisition;
7. drag and Confirm idempotence survives reacquisition without duplicate actions;
8. build logs identify package version, native source commit, policy version, and tablemap version.

A failed or ambiguous individual scrape may suppress an unsafe click, but it must not suppress future scrapes or future valid decisions.
