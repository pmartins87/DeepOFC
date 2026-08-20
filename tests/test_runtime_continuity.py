import pytest

from deepofc.runtime_continuity import (
    CanonicalScreenState,
    ContinuityPhase,
    ContinuitySupervisor,
    RuntimeMode,
    ScrapeResult,
)


def normal_state(fingerprint: str, round_index: int, actionable: bool = False):
    return CanonicalScreenState(
        fingerprint=fingerprint,
        mode=RuntimeMode.NORMAL,
        round_index=round_index,
        hero_actionable=actionable,
    )


def fantasy_state(fingerprint: str, card_count: int, actionable: bool = False):
    return CanonicalScreenState(
        fingerprint=fingerprint,
        mode=RuntimeMode.FANTASY,
        round_index=-1,
        hero_actionable=actionable,
        fantasy_card_count=card_count,
    )


def event_codes(decision):
    return [event.code for event in decision.events]


def test_bootstrap_accepts_normal_mid_hand_candidate_without_process_history():
    supervisor = ContinuitySupervisor()

    decision = supervisor.observe(ScrapeResult(normal_state("r3-current", 3, True)))

    assert decision.phase is ContinuityPhase.TRACKING
    assert decision.authoritative_state.round_index == 3
    assert decision.state_replaced
    assert event_codes(decision) == ["BOOTSTRAP_ACCEPT"]


@pytest.mark.parametrize("card_count", [14, 15, 16, 17])
def test_bootstrap_models_one_generic_fantasy_mode_for_all_supported_counts(card_count):
    supervisor = ContinuitySupervisor()

    decision = supervisor.observe(
        ScrapeResult(fantasy_state(f"fantasy-{card_count}", card_count, True))
    )

    assert decision.phase is ContinuityPhase.TRACKING
    assert decision.authoritative_state.mode is RuntimeMode.FANTASY
    assert decision.authoritative_state.fantasy_card_count == card_count
    assert event_codes(decision) == ["BOOTSTRAP_ACCEPT"]


def test_changed_identity_fault_cannot_permanently_freeze_wait_next():
    supervisor = ContinuitySupervisor(transient_reject_limit=2)
    supervisor.observe(ScrapeResult(normal_state("round-3", 3)))
    supervisor.wait_for_transition(expected_round=4)

    first = supervisor.observe(
        ScrapeResult(
            None,
            raw_changed=True,
            error_code="HERO_INCOMING_IDENTITY_CHANGED",
            error_detail="Hero incoming card identities changed within the same round",
        )
    )
    second = supervisor.observe(
        ScrapeResult(
            None,
            raw_changed=True,
            error_code="HERO_INCOMING_IDENTITY_CHANGED",
            error_detail="Hero incoming card identities changed within the same round",
        )
    )

    assert first.phase is ContinuityPhase.WAIT_TRANSITION
    assert second.phase is ContinuityPhase.REACQUIRE
    assert event_codes(second) == ["SCRAPE_FAULT", "REACQUIRE_BEGIN"]
    assert supervisor.authoritative_state.fingerprint == "round-3"

    recovered = supervisor.observe(ScrapeResult(normal_state("round-4", 4, True)))
    assert recovered.phase is ContinuityPhase.TRACKING
    assert recovered.authoritative_state.fingerprint == "round-4"
    assert event_codes(recovered) == ["REACQUIRE_ACCEPT"]


def test_faults_are_logged_but_there_is_no_terminal_blocked_phase():
    supervisor = ContinuitySupervisor(transient_reject_limit=1)

    for code in (
        "UNKNOWN_CARD",
        "NO_UNIQUE_DEALER",
        "RANK_LOW_CONFIDENCE",
        "TRANSIENT_ANIMATION",
    ):
        decision = supervisor.observe(
            ScrapeResult(None, raw_changed=True, error_code=code)
        )
        assert decision.phase is ContinuityPhase.REACQUIRE
        assert "SCRAPE_FAULT" in event_codes(decision)

    recovered = supervisor.observe(ScrapeResult(normal_state("clean", 2, True)))
    assert recovered.phase is ContinuityPhase.TRACKING
    assert recovered.authoritative_state.fingerprint == "clean"
    assert event_codes(recovered) == ["REACQUIRE_ACCEPT"]


def test_valid_current_screen_wins_over_stale_transition_expectation():
    supervisor = ContinuitySupervisor()
    supervisor.observe(ScrapeResult(normal_state("old-r3", 3)))
    supervisor.wait_for_transition(expected_round=4)

    # A valid changed current screen that does not fit stale process lineage is
    # still authoritative. This covers reconnect/new-hand/Fantasy transitions.
    decision = supervisor.observe(
        ScrapeResult(fantasy_state("current-fantasy", 16, True), raw_changed=True)
    )

    assert decision.phase is ContinuityPhase.TRACKING
    assert decision.authoritative_state.fingerprint == "current-fantasy"
    assert event_codes(decision) == [
        "CONTINUITY_MISMATCH",
        "SCREEN_AUTHORITY_ACCEPT",
    ]


def test_expected_next_round_is_accepted_exactly_once_then_becomes_stable():
    supervisor = ContinuitySupervisor()
    supervisor.observe(ScrapeResult(normal_state("round-2", 2)))
    supervisor.wait_for_transition(expected_round=3)

    advanced = supervisor.observe(ScrapeResult(normal_state("round-3", 3, True)))
    repeated = supervisor.observe(ScrapeResult(normal_state("round-3", 3, True)))

    assert advanced.state_replaced
    assert event_codes(advanced) == ["TRANSITION_ACCEPT"]
    assert not repeated.state_replaced
    assert event_codes(repeated) == ["STATE_STABLE"]


def test_force_reacquire_discards_stale_transition_expectation():
    supervisor = ContinuitySupervisor()
    supervisor.observe(ScrapeResult(normal_state("round-1", 1)))
    supervisor.wait_for_transition(expected_round=2)

    event = supervisor.force_reacquire("executor requested fresh current-screen state")

    assert event.code == "REACQUIRE_BEGIN"
    assert supervisor.phase is ContinuityPhase.REACQUIRE
    assert supervisor.expected_round is None
    assert supervisor.reacquire_generation == 1


def test_invalid_fantasy_counts_are_not_separate_modes():
    with pytest.raises(ValueError, match="14..17"):
        fantasy_state("bad", 13)

    with pytest.raises(ValueError, match="14..17"):
        fantasy_state("bad", 18)
