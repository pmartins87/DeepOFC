from __future__ import annotations

"""Research-only physically consistent hidden-world sampler.

This sampler exists to support external search/ISMCTS experiments without
repeating a failure mode found in public Monte Carlo OFC solvers: sampling hero
and opponent futures independently from the same undepleted deck can assign the
same physical card to both futures.

Authority is deliberately narrow:
  UNIFORM_CONDITIONAL_PHYSICAL_WORLD_SAMPLER_SCREENING_ONLY

It samples uniformly from the remaining physical deck conditional only on the
explicitly known cards.  It does NOT condition on strategic public-action
history and therefore is not a posterior-belief authority for DeepOFC.
"""

from dataclasses import dataclass
import random
from typing import Iterable, Sequence

from engine import Card, full_deck

AUTHORITY = "UNIFORM_CONDITIONAL_PHYSICAL_WORLD_SAMPLER_SCREENING_ONLY"
SCHEMA = "openofc-external-world-sampler-v1"


@dataclass(frozen=True)
class HiddenZone:
    name: str
    cards: tuple[Card, ...]


@dataclass(frozen=True)
class SampledPhysicalWorld:
    schema: str
    authority: str
    seed: int | str | None
    known_cards: tuple[Card, ...]
    zones: tuple[HiddenZone, ...]
    undealt: tuple[Card, ...]

    def all_cards(self) -> tuple[Card, ...]:
        out = list(self.known_cards)
        for zone in self.zones:
            out.extend(zone.cards)
        out.extend(self.undealt)
        return tuple(out)

    def zone(self, name: str) -> tuple[Card, ...]:
        matches = [zone.cards for zone in self.zones if zone.name == name]
        if len(matches) != 1:
            raise KeyError(name)
        return matches[0]


def sample_physical_world(
    *,
    known_cards: Iterable[Card],
    zone_sizes: Sequence[tuple[str, int]],
    seed: int | str | None,
) -> SampledPhysicalWorld:
    known = tuple(known_cards)
    if len(known) != len(set(known)):
        raise ValueError("known_cards contain duplicate physical cards")

    names = [str(name) for name, _ in zone_sizes]
    if any(not name for name in names):
        raise ValueError("hidden-zone names must be non-empty")
    if len(names) != len(set(names)):
        raise ValueError("hidden-zone names must be unique")
    if any(int(size) < 0 for _name, size in zone_sizes):
        raise ValueError("hidden-zone sizes must be non-negative")

    deck = list(full_deck(2))
    deck_set = set(deck)
    if any(card not in deck_set for card in known):
        raise ValueError("known card is outside the 54-card target deck")
    remaining = [card for card in deck if card not in set(known)]
    requested = sum(int(size) for _name, size in zone_sizes)
    if requested > len(remaining):
        raise ValueError("hidden-zone request exceeds remaining physical deck")

    rng = random.Random(seed)
    rng.shuffle(remaining)

    zones: list[HiddenZone] = []
    cursor = 0
    for name, size in zone_sizes:
        count = int(size)
        cards = tuple(remaining[cursor : cursor + count])
        cursor += count
        zones.append(HiddenZone(str(name), cards))

    world = SampledPhysicalWorld(
        schema=SCHEMA,
        authority=AUTHORITY,
        seed=seed,
        known_cards=known,
        zones=tuple(zones),
        undealt=tuple(remaining[cursor:]),
    )
    _validate_conservation(world)
    return world


def _validate_conservation(world: SampledPhysicalWorld) -> None:
    cards = world.all_cards()
    target = tuple(full_deck(2))
    if len(cards) != 54:
        raise AssertionError("sampled world must account for exactly 54 physical cards")
    if len(set(cards)) != 54:
        raise AssertionError("sampled world assigned one physical card more than once")
    if set(cards) != set(target):
        raise AssertionError("sampled world must conserve the exact target deck")


__all__ = [
    "AUTHORITY",
    "SCHEMA",
    "HiddenZone",
    "SampledPhysicalWorld",
    "sample_physical_world",
]
