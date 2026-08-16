from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .actions import NormalPlacementAction, enumerate_normal_actions
from .simulator import DeterministicDeck, apply_normal_action
from .state import Card, OFCState, PlayerBoard, PlayerState


def _public_placements(action: NormalPlacementAction) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((p.card.code, p.row.value) for p in action.placements))


@dataclass(frozen=True)
class SequentialActionRecord:
    """Authoritative action record.

    `action` contains the acting player's private discard. It belongs only to the
    authoritative engine and that player's perfect-recall observation. Opponent
    projections must use `public_record()` instead.
    """

    round_index: int
    chair: int
    action: NormalPlacementAction

    def public_record(self) -> "PublicActionRecord":
        return PublicActionRecord(
            round_index=self.round_index,
            chair=self.chair,
            placements=_public_placements(self.action),
        )


@dataclass(frozen=True)
class PublicActionRecord:
    round_index: int
    chair: int
    placements: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class HUPlayerObservation:
    """Explicit player-information projection with perfect recall.

    The canonical `state` exposes the player's own current incoming cards and
    own past discard identities. Opponent current incoming/discard identities
    are represented only by counts in PlayerState. `own_action_history` keeps
    exact private actions for perfect recall; `public_action_history` contains
    confirmed placements only and never an opponent discard.
    """

    state: OFCState
    own_action_history: tuple[tuple, ...]
    public_action_history: tuple[PublicActionRecord, ...]

    @property
    def hero_chair(self) -> int:
        return self.state.hero_chair


@dataclass(frozen=True)
class HUSequentialNormalState:
    """Authoritative five-round HU Pineapple/Joker normal-play state.

    Public construction and `apply()` perform the full physical/progress audit.
    Exact solver traversals may use `apply_fast()` only when starting from a
    previously validated state. `apply_fast()` still runs the canonical
    `apply_normal_action` fail-closed semantic checks; it skips only the repeated
    whole-state partition/progress audit on the *derived* immutable state.

    The fast/audited paths are regression-cross-checked in `test_sequential.py`.
    The private `_trusted_derived` marker is excluded from equality/hash so the
    same semantic state compares identically regardless of which path created it.
    """

    deck: DeterministicDeck
    boards: tuple[PlayerBoard, PlayerBoard]
    incoming: tuple[tuple[Card, ...], tuple[Card, ...]]
    discards: tuple[tuple[Card, ...], tuple[Card, ...]]
    history: tuple[SequentialActionRecord, ...]
    round_index: int
    actor_in_round: int
    first_player: int
    dealer_chair: int
    terminal: bool = False
    _trusted_derived: bool = field(
        default=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if self._trusted_derived:
            return
        self.assert_fully_valid()

    def assert_fully_valid(self) -> None:
        """Run the complete authoritative state audit on demand."""
        if self.first_player not in (0, 1):
            raise ValueError("first_player must be 0 or 1")
        if self.dealer_chair not in (0, 1):
            raise ValueError("dealer_chair must be 0 or 1")
        if self.round_index not in range(5):
            raise ValueError("normal sequential round_index must be 0..4")
        if self.actor_in_round not in (0, 1):
            raise ValueError("actor_in_round must be 0 or 1")
        if len(self.boards) != 2 or len(self.incoming) != 2 or len(self.discards) != 2:
            raise ValueError("HU sequential state requires exactly two players")
        self._validate_authoritative_physical_state()
        self._validate_progress_shape()

    @classmethod
    def new(
        cls,
        *,
        seed: int,
        first_player: int = 0,
        dealer_chair: int | None = None,
    ) -> "HUSequentialNormalState":
        if first_player not in (0, 1):
            raise ValueError("first_player must be 0 or 1")
        if dealer_chair is None:
            dealer_chair = first_player
        deck = DeterministicDeck.shuffled(seed)
        incoming, deck = cls._deal_private_batches(deck, round_index=0, first_player=first_player)
        return cls(
            deck=deck,
            boards=(PlayerBoard(), PlayerBoard()),
            incoming=incoming,
            discards=((), ()),
            history=(),
            round_index=0,
            actor_in_round=0,
            first_player=first_player,
            dealer_chair=dealer_chair,
            terminal=False,
        )

    @staticmethod
    def _deal_private_batches(
        deck: DeterministicDeck,
        *,
        round_index: int,
        first_player: int,
    ) -> tuple[tuple[tuple[Card, ...], tuple[Card, ...]], DeterministicDeck]:
        count = 5 if round_index == 0 else 3
        first_cards, deck = deck.draw(count)
        second_cards, deck = deck.draw(count)
        batches: list[tuple[Card, ...]] = [(), ()]
        batches[first_player] = first_cards
        batches[1 - first_player] = second_cards
        return (batches[0], batches[1]), deck

    @property
    def acting_chair(self) -> int:
        if self.terminal:
            return 1 - self.first_player
        return self.first_player if self.actor_in_round == 0 else 1 - self.first_player

    @property
    def actions_taken(self) -> int:
        return len(self.history)

    def _drawn_cards(self) -> tuple[Card, ...]:
        return self.deck.cards[: self.deck.cursor]

    def _authoritative_known_cards(self) -> tuple[Card, ...]:
        return (
            *self.boards[0].cards(),
            *self.boards[1].cards(),
            *self.incoming[0],
            *self.incoming[1],
            *self.discards[0],
            *self.discards[1],
        )

    def _validate_authoritative_physical_state(self) -> None:
        known = self._authoritative_known_cards()
        if len(known) != len(set(known)):
            raise ValueError("duplicate physical card in authoritative HU state")
        drawn = self._drawn_cards()
        if len(drawn) != len(set(drawn)):
            raise ValueError("deterministic deck drawn prefix contains duplicates")
        if set(known) != set(drawn) or len(known) != len(drawn):
            raise ValueError(
                "authoritative boards/incoming/discards must partition exactly the drawn deck prefix"
            )

    def _validate_progress_shape(self) -> None:
        expected_actions = 2 * self.round_index + self.actor_in_round
        if self.terminal:
            expected_actions = 10
        if len(self.history) != expected_actions:
            raise ValueError(
                f"history length mismatch: got {len(self.history)}, expected {expected_actions}"
            )

        for chair in (0, 1):
            acted_this_round = any(
                record.round_index == self.round_index and record.chair == chair
                for record in self.history
            )
            expected_incoming = 0 if acted_this_round else (5 if self.round_index == 0 else 3)
            if self.terminal:
                expected_incoming = 0
            if len(self.incoming[chair]) != expected_incoming:
                raise ValueError(
                    f"chair {chair} incoming shape mismatch in round {self.round_index}: "
                    f"got {len(self.incoming[chair])}, expected {expected_incoming}"
                )

            if self.terminal:
                expected_board = 13
            elif self.round_index == 0:
                expected_board = 5 if acted_this_round else 0
            else:
                expected_board = 5 + 2 * (self.round_index - 1)
                if acted_this_round:
                    expected_board += 2
            if self.boards[chair].filled_count() != expected_board:
                raise ValueError(
                    f"chair {chair} board count mismatch: got {self.boards[chair].filled_count()}, "
                    f"expected {expected_board}"
                )

            if self.terminal:
                expected_discards = 4
            elif self.round_index == 0:
                expected_discards = 0
            else:
                expected_discards = self.round_index - 1
                if acted_this_round:
                    expected_discards += 1
            if len(self.discards[chair]) != expected_discards:
                raise ValueError(
                    f"chair {chair} discard count mismatch: got {len(self.discards[chair])}, "
                    f"expected {expected_discards}"
                )

    def observation(self, hero_chair: int) -> HUPlayerObservation:
        if hero_chair not in (0, 1):
            raise ValueError("hero_chair must be 0 or 1")
        opponent = 1 - hero_chair
        action_required = (not self.terminal) and self.acting_chair == hero_chair

        players = (
            PlayerState(
                chair=0,
                board=self.boards[0],
                hidden_discard_count=(0 if hero_chair == 0 else len(self.discards[0])),
                hidden_incoming_count=(0 if hero_chair == 0 else len(self.incoming[0])),
            ),
            PlayerState(
                chair=1,
                board=self.boards[1],
                hidden_discard_count=(0 if hero_chair == 1 else len(self.discards[1])),
                hidden_incoming_count=(0 if hero_chair == 1 else len(self.incoming[1])),
            ),
        )
        canonical = OFCState(
            players=players,
            hero_chair=hero_chair,
            dealer_chair=self.dealer_chair,
            acting_chair=self.acting_chair,
            round_index=self.round_index,
            hero_incoming=self.incoming[hero_chair],
            hero_discards=self.discards[hero_chair],
            hero_can_prepare=action_required,
            hero_can_confirm=action_required,
            action_required=action_required,
        )
        own_history = tuple(
            record.action.key() for record in self.history if record.chair == hero_chair
        )
        public_history = tuple(record.public_record() for record in self.history)
        observation = HUPlayerObservation(
            state=canonical,
            own_action_history=own_history,
            public_action_history=public_history,
        )

        forbidden = set(self.incoming[opponent]) | set(self.discards[opponent])
        leaked = forbidden & set(canonical.known_cards())
        if leaked:
            raise AssertionError(f"opponent private card leaked into observation: {leaked}")
        return observation

    def legal_actions(self) -> tuple[NormalPlacementAction, ...]:
        if self.terminal:
            return ()
        return enumerate_normal_actions(self.observation(self.acting_chair).state)

    def _advance(
        self,
        action: NormalPlacementAction,
        *,
        audit_derived_state: bool,
    ) -> "HUSequentialNormalState":
        if self.terminal:
            raise ValueError("cannot act after terminal state")
        chair = self.acting_chair

        # This remains the semantic gate for every fast or audited transition.
        new_board, discarded = apply_normal_action(
            self.boards[chair],
            action,
            round_index=self.round_index,
            incoming=self.incoming[chair],
        )
        boards = list(self.boards)
        boards[chair] = new_board
        incoming = list(self.incoming)
        incoming[chair] = ()
        discards = list(self.discards)
        discards[chair] = (*discards[chair], *discarded)
        history = (*self.history, SequentialActionRecord(self.round_index, chair, action))
        trusted = not audit_derived_state

        if self.actor_in_round == 0:
            return HUSequentialNormalState(
                deck=self.deck,
                boards=(boards[0], boards[1]),
                incoming=(incoming[0], incoming[1]),
                discards=(discards[0], discards[1]),
                history=history,
                round_index=self.round_index,
                actor_in_round=1,
                first_player=self.first_player,
                dealer_chair=self.dealer_chair,
                terminal=False,
                _trusted_derived=trusted,
            )

        if self.round_index == 4:
            return HUSequentialNormalState(
                deck=self.deck,
                boards=(boards[0], boards[1]),
                incoming=((), ()),
                discards=(discards[0], discards[1]),
                history=history,
                round_index=4,
                actor_in_round=1,
                first_player=self.first_player,
                dealer_chair=self.dealer_chair,
                terminal=True,
                _trusted_derived=trusted,
            )

        next_round = self.round_index + 1
        next_incoming, next_deck = self._deal_private_batches(
            self.deck,
            round_index=next_round,
            first_player=self.first_player,
        )
        return HUSequentialNormalState(
            deck=next_deck,
            boards=(boards[0], boards[1]),
            incoming=next_incoming,
            discards=(discards[0], discards[1]),
            history=history,
            round_index=next_round,
            actor_in_round=0,
            first_player=self.first_player,
            dealer_chair=self.dealer_chair,
            terminal=False,
            _trusted_derived=trusted,
        )

    def apply(self, action: NormalPlacementAction) -> "HUSequentialNormalState":
        """Apply one action and fully audit the derived authoritative state."""
        return self._advance(action, audit_derived_state=True)

    def apply_fast(self, action: NormalPlacementAction) -> "HUSequentialNormalState":
        """Apply one action with semantic validation but skip repeated state audit.

        Use only for recursive solver/reference traversal from a state already
        known to be valid. Call `assert_fully_valid()` at audit boundaries.
        """
        return self._advance(action, audit_derived_state=False)

    def apply_key(self, action_key: tuple) -> "HUSequentialNormalState":
        for action in self.legal_actions():
            if action.key() == action_key:
                return self.apply(action)
        raise ValueError("recorded action key is not legal in current replay state")


def replay_hu_normal_hand(
    *,
    seed: int,
    action_keys: Sequence[tuple],
    first_player: int = 0,
    dealer_chair: int | None = None,
) -> HUSequentialNormalState:
    """Replay one complete or partial seeded HU normal hand deterministically."""

    state = HUSequentialNormalState.new(
        seed=seed,
        first_player=first_player,
        dealer_chair=dealer_chair,
    )
    for key in action_keys:
        state = state.apply_key(key)
    return state


def deterministic_first_legal_hand(
    *, seed: int, first_player: int = 0, dealer_chair: int | None = None
) -> HUSequentialNormalState:
    """Complete a hand using the first canonical legal action at every node.

    This is a structural replay/fuzz helper only, never a poker strategy.
    """

    state = HUSequentialNormalState.new(
        seed=seed,
        first_player=first_player,
        dealer_chair=dealer_chair,
    )
    while not state.terminal:
        legal = state.legal_actions()
        if not legal:
            raise AssertionError("nonterminal sequential state has no legal actions")
        state = state.apply(legal[0])
    return state
