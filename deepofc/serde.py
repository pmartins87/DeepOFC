from __future__ import annotations

from typing import Any

from .state import Card, OFCState, PendingPlacement, PlayerBoard, PlayerState, Row


def _cards(values: list[str]) -> tuple[Card, ...]:
    return tuple(Card.from_code(v) for v in values)


def board_from_dict(data: dict[str, Any]) -> PlayerBoard:
    return PlayerBoard(
        top=_cards(list(data.get("top", []))),
        middle=_cards(list(data.get("middle", []))),
        bottom=_cards(list(data.get("bottom", []))),
    )


def state_from_dict(data: dict[str, Any]) -> OFCState:
    players = []
    for raw in data["players"]:
        players.append(
            PlayerState(
                chair=int(raw["chair"]),
                board=board_from_dict(raw.get("board", {})),
                name=str(raw.get("name", "")),
                fantasy=bool(raw.get("fantasy", False)),
                sitting_out=bool(raw.get("sitting_out", False)),
                hidden_discard_count=int(raw.get("hidden_discard_count", 0)),
                hidden_incoming_count=int(raw.get("hidden_incoming_count", 0)),
            )
        )
    pending = tuple(
        PendingPlacement(
            card=Card.from_code(p["card"]),
            row=Row(str(p["row"])),
        )
        for p in data.get("hero_pending", [])
    )
    return OFCState(
        players=tuple(players),
        hero_chair=int(data["hero_chair"]),
        dealer_chair=int(data["dealer_chair"]),
        acting_chair=int(data["acting_chair"]),
        round_index=int(data["round_index"]),
        hero_incoming=_cards(list(data.get("hero_incoming", []))),
        hero_discards=_cards(list(data.get("hero_discards", []))),
        hero_pending=pending,
        hero_can_prepare=bool(data.get("hero_can_prepare", False)),
        hero_can_confirm=bool(data.get("hero_can_confirm", False)),
        action_required=bool(data.get("action_required", False)),
        mode=str(data.get("mode", "joker_ultimate")),
    )
