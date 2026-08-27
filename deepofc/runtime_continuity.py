from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeMode(str, Enum):
    NORMAL = "normal"
    FANTASY = "fantasy"


class ContinuityPhase(str, Enum):
    BOOTSTRAP = "bootstrap"
    TRACKING = "tracking"
    WAIT_TRANSITION = "wait_transition"
    REACQUIRE = "reacquire"


@dataclass(frozen=True)
class CanonicalScreenState:
    """Self-consistent state reconstructed from the current visible game.

    The continuity layer deliberately models Fantasy as one generic mode. The
    number of Fantasy cards is data (`fantasy_card_count`), never a mode name.
    """

    fingerprint: str
    mode: RuntimeMode
    round_index: int
    hero_actionable: bool = False
    fantasy_card_count: int | None = None

    def __post_init__(self) -> None:
        if not self.fingerprint:
            raise ValueError("fingerprint must be non-empty")
        if self.mode is RuntimeMode.NORMAL:
            if self.round_index not in range(5):
                raise ValueError("normal round_index must be 0..4")
            if self.fantasy_card_count is not None:
                raise ValueError("normal state cannot carry fantasy_card_count")
        else:
            if self.round_index != -1:
                raise ValueError("Fantasy uses round_index=-1")
            if self.fantasy_card_count not in range(14, 18):
                raise ValueError("Fantasy card count must be 14..17")


@dataclass(frozen=True)
class ScrapeResult:
    state: CanonicalScreenState | None
    raw_changed: bool = False
    error_code: str = ""
    error_detail: str = ""

    def __post_init__(self) -> None:
        if self.state is None and not self.error_code:
            raise ValueError("invalid scrape must carry an error_code")
        if self.state is not None and self.error_code:
            raise ValueError("valid scrape cannot also carry an error_code")


@dataclass(frozen=True)
class ContinuityEvent:
    code: str
    detail: str = ""


@dataclass(frozen=True)
class ContinuityDecision:
    phase: ContinuityPhase
    authoritative_state: CanonicalScreenState | None
    state_replaced: bool
    events: tuple[ContinuityEvent, ...]


class ContinuitySupervisor:
    """Never-terminal supervisor for scrape/reconstruction continuity.

    Perception failures are logged and retried. They may temporarily prevent a
    click because no safe state exists for that scrape, but they never place the
    runtime into a permanent blocked state. A self-consistent reconstruction of
    the current screen always has a path to become authoritative.

    This class intentionally owns only *state continuity*. Transactional drag /
    Confirm idempotence remains a separate executor concern. When reacquisition
    replaces the authoritative state, the executor must discard its stale plan
    and re-plan from the accepted current-screen state.
    """

    def __init__(self, *, transient_reject_limit: int = 2) -> None:
        if transient_reject_limit < 1:
            raise ValueError("transient_reject_limit must be >= 1")
        self.transient_reject_limit = transient_reject_limit
        self.phase = ContinuityPhase.BOOTSTRAP
        self.authoritative_state: CanonicalScreenState | None = None
        self.expected_round: int | None = None
        self.reject_streak = 0
        self.reacquire_generation = 0

    def wait_for_transition(self, *, expected_round: int | None = None) -> None:
        if expected_round is not None and expected_round not in range(5):
            raise ValueError("expected_round must be 0..4 or None")
        self.phase = ContinuityPhase.WAIT_TRANSITION
        self.expected_round = expected_round
        self.reject_streak = 0

    def force_reacquire(self, reason: str) -> ContinuityEvent:
        self.phase = ContinuityPhase.REACQUIRE
        self.expected_round = None
        self.reject_streak = 0
        self.reacquire_generation += 1
        return ContinuityEvent("REACQUIRE_BEGIN", reason)

    def observe(self, result: ScrapeResult) -> ContinuityDecision:
        events: list[ContinuityEvent] = []

        if result.state is None:
            self.reject_streak += 1
            detail = result.error_detail or result.error_code
            events.append(
                ContinuityEvent(
                    "SCRAPE_FAULT",
                    f"{result.error_code}: {detail}; streak={self.reject_streak}",
                )
            )
            if (
                result.raw_changed
                and self.reject_streak >= self.transient_reject_limit
                and self.phase is not ContinuityPhase.REACQUIRE
            ):
                previous_phase = self.phase
                events.append(
                    self.force_reacquire(
                        f"{previous_phase.value} stale after changed rejected scrapes"
                    )
                )
            return ContinuityDecision(
                phase=self.phase,
                authoritative_state=self.authoritative_state,
                state_replaced=False,
                events=tuple(events),
            )

        candidate = result.state
        self.reject_streak = 0

        if self.phase in (ContinuityPhase.BOOTSTRAP, ContinuityPhase.REACQUIRE):
            old_phase = self.phase
            self.authoritative_state = candidate
            self.phase = ContinuityPhase.TRACKING
            self.expected_round = None
            code = (
                "BOOTSTRAP_ACCEPT"
                if old_phase is ContinuityPhase.BOOTSTRAP
                else "REACQUIRE_ACCEPT"
            )
            events.append(
                ContinuityEvent(
                    code,
                    f"mode={candidate.mode.value} round={candidate.round_index} "
                    f"fingerprint={candidate.fingerprint}",
                )
            )
            return ContinuityDecision(
                phase=self.phase,
                authoritative_state=candidate,
                state_replaced=True,
                events=tuple(events),
            )

        if self.authoritative_state is None:
            # Defensive self-heal: TRACKING/WAIT without an accepted state is
            # treated exactly like a process restart, never as a terminal error.
            self.phase = ContinuityPhase.BOOTSTRAP
            return self.observe(result)

        if candidate.fingerprint == self.authoritative_state.fingerprint:
            events.append(ContinuityEvent("STATE_STABLE", candidate.fingerprint))
            return ContinuityDecision(
                phase=self.phase,
                authoritative_state=self.authoritative_state,
                state_replaced=False,
                events=tuple(events),
            )

        if self.phase is ContinuityPhase.WAIT_TRANSITION:
            if (
                candidate.mode is RuntimeMode.NORMAL
                and self.expected_round is not None
                and candidate.round_index == self.expected_round
            ):
                events.append(
                    ContinuityEvent(
                        "TRANSITION_ACCEPT",
                        f"expected_round={self.expected_round}",
                    )
                )
            else:
                # Current-screen authority wins over stale lineage. A valid
                # changed state is accepted rather than freezing on the old one.
                events.append(
                    ContinuityEvent(
                        "CONTINUITY_MISMATCH",
                        "valid changed state did not match stored transition expectation",
                    )
                )
                events.append(
                    ContinuityEvent(
                        "SCREEN_AUTHORITY_ACCEPT",
                        f"mode={candidate.mode.value} round={candidate.round_index}",
                    )
                )
        else:
            events.append(
                ContinuityEvent(
                    "STATE_CHANGE_ACCEPT",
                    f"mode={candidate.mode.value} round={candidate.round_index}",
                )
            )

        self.authoritative_state = candidate
        self.phase = ContinuityPhase.TRACKING
        self.expected_round = None
        return ContinuityDecision(
            phase=self.phase,
            authoritative_state=candidate,
            state_replaced=True,
            events=tuple(events),
        )
