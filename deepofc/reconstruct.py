from __future__ import annotations

from dataclasses import dataclass

from .observation import RawOFCObservation
from .state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


class ReconstructionError(ValueError):
    pass


def _sorted_cards(cards) -> tuple[Card, ...]:
    return tuple(sorted(cards, key=lambda c: c.code))


def _normalize_board(board: PlayerBoard) -> PlayerBoard:
    return PlayerBoard(
        top=_sorted_cards(board.top),
        middle=_sorted_cards(board.middle),
        bottom=_sorted_cards(board.bottom),
    )


def _row_of(board: PlayerBoard, card: Card) -> Row | None:
    for row in Row:
        if card in board.row(row):
            return row
    return None


def _board_from_membership(membership: dict[Row, set[Card]]) -> PlayerBoard:
    return PlayerBoard(
        top=_sorted_cards(membership[Row.TOP]),
        middle=_sorted_cards(membership[Row.MIDDLE]),
        bottom=_sorted_cards(membership[Row.BOTTOM]),
    )


def _membership(board: PlayerBoard) -> dict[Row, set[Card]]:
    return {row: set(board.row(row)) for row in Row}


def _ensure_committed_cards_still_visible(committed: PlayerBoard, visual: PlayerBoard) -> None:
    for row in Row:
        missing = set(committed.row(row)) - set(visual.row(row))
        if missing:
            codes = ",".join(sorted(c.code for c in missing))
            raise ReconstructionError(
                f"previously committed cards moved/disappeared from {row.value}: {codes}"
            )


def _advance_hero_committed_board(
    previous: OFCState,
    observation: RawOFCObservation,
) -> PlayerBoard:
    """Apply the previous round's completed Hero action using new evidence.

    Sparse replay sampling may miss the exact Confirm frame. The next round's
    discard tracker identifies the discarded prior incoming card, while the
    current visual rows reveal where the remaining prior incoming cards became
    committed. We intentionally do not trust the previous tentative row layout
    because Hero may rearrange it before Confirm.
    """

    previous_board = previous.player(previous.hero_chair).board
    visual = observation.player(observation.hero_chair).visual_board
    _ensure_committed_cards_still_visible(previous_board, visual)

    old_discards = set(previous.hero_discards)
    new_tracker = set(observation.hero_discard_tracker)
    if not old_discards.issubset(new_tracker):
        raise ReconstructionError("Hero discard tracker lost a previously known discard")
    discard_delta = new_tracker - old_discards

    expected_discards = 0 if previous.round_index == 0 else 1
    if len(discard_delta) != expected_discards:
        raise ReconstructionError(
            f"round transition expected {expected_discards} new Hero discard(s), got {len(discard_delta)}"
        )

    prior_incoming = set(previous.hero_incoming)
    if not prior_incoming:
        raise ReconstructionError("cannot advance round without previous Hero incoming cards")
    if not discard_delta.issubset(prior_incoming):
        raise ReconstructionError("new Hero discard was not part of previous incoming cards")

    committed_from_prior = prior_incoming - discard_delta
    expected_commit_count = 5 if previous.round_index == 0 else 2
    if len(committed_from_prior) != expected_commit_count:
        raise ReconstructionError(
            f"previous round should commit {expected_commit_count} cards, got {len(committed_from_prior)}"
        )

    membership = _membership(previous_board)
    for card in committed_from_prior:
        row = _row_of(visual, card)
        if row is None:
            raise ReconstructionError(
                f"previous incoming card {card.code} is neither discarded nor visible as committed"
            )
        membership[row].add(card)

    advanced = _board_from_membership(membership)
    _ensure_committed_cards_still_visible(advanced, visual)
    return advanced


def reconstruct_observation(
    observation: RawOFCObservation,
    previous: OFCState | None = None,
) -> OFCState:
    """Convert one raw visual frame into canonical DeepOFC state.

    The function is intentionally history-dependent. Mid-hand attachment without
    prior canonical state is rejected unless the observation is round 0, because
    a single KKPoker image cannot reliably distinguish committed Hero row cards
    from tentative pre-Confirm placements.
    """

    if previous is None:
        if observation.round_index != 0:
            raise ReconstructionError(
                "mid-hand observation requires prior canonical state to distinguish committed/pending Hero cards"
            )
        hero_committed = PlayerBoard()
    else:
        if observation.mode != previous.mode:
            raise ReconstructionError("mode changed inside hand")
        if observation.hero_chair != previous.hero_chair:
            raise ReconstructionError("Hero chair changed inside hand")
        if observation.dealer_chair != previous.dealer_chair:
            raise ReconstructionError("dealer chair changed inside hand")
        if observation.round_index < previous.round_index:
            raise ReconstructionError("round moved backwards")
        if observation.round_index > previous.round_index + 1:
            raise ReconstructionError("skipped more than one round between observations")

        if observation.round_index == previous.round_index + 1:
            hero_committed = _advance_hero_committed_board(previous, observation)
        else:
            hero_committed = previous.player(previous.hero_chair).board
            _ensure_committed_cards_still_visible(
                hero_committed,
                observation.player(observation.hero_chair).visual_board,
            )

    hero_visual = observation.player(observation.hero_chair).visual_board
    committed_cards = set(hero_committed.cards())
    pending: list[PendingPlacement] = []
    for row in Row:
        for card in hero_visual.row(row):
            if card not in committed_cards:
                pending.append(PendingPlacement(card=card, row=row))

    pending_cards = {p.card for p in pending}
    loose_cards = set(observation.hero_loose_cards)
    if pending_cards & loose_cards:
        raise ReconstructionError("same Hero current card is both loose and tentatively placed")
    current_incoming = pending_cards | loose_cards

    if previous is not None and observation.round_index == previous.round_index:
        if set(previous.hero_incoming) != current_incoming:
            raise ReconstructionError(
                "Hero incoming card identities changed within the same round"
            )

    expected_incoming = 5 if observation.round_index == 0 else 3
    if len(current_incoming) != expected_incoming:
        raise ReconstructionError(
            f"normal round {observation.round_index} requires {expected_incoming} visible Hero incoming cards; got {len(current_incoming)}"
        )

    players: list[PlayerState] = []
    for raw_player in observation.players:
        if raw_player.chair == observation.hero_chair:
            board = _normalize_board(hero_committed)
        else:
            board = _normalize_board(raw_player.visual_board)
            if previous is not None:
                old = previous.player(raw_player.chair).board
                for row in Row:
                    if not set(old.row(row)).issubset(set(board.row(row))):
                        raise ReconstructionError(
                            f"opponent committed card moved/disappeared from {row.value}"
                        )
        players.append(
            PlayerState(
                chair=raw_player.chair,
                board=board,
                name=raw_player.name,
                fantasy=raw_player.fantasy,
                sitting_out=raw_player.sitting_out,
                hidden_discard_count=raw_player.hidden_discard_count,
                hidden_incoming_count=raw_player.hidden_incoming_count,
            )
        )

    return OFCState(
        players=tuple(players),
        hero_chair=observation.hero_chair,
        dealer_chair=observation.dealer_chair,
        acting_chair=observation.acting_chair,
        round_index=observation.round_index,
        hero_incoming=_sorted_cards(current_incoming),
        hero_discards=_sorted_cards(observation.hero_discard_tracker),
        hero_pending=tuple(sorted(pending, key=lambda p: (p.row.value, p.card.code))),
        hero_can_prepare=observation.hero_can_prepare,
        hero_can_confirm=observation.hero_can_confirm,
        action_required=observation.hero_can_confirm,
        mode=observation.mode,
    )
