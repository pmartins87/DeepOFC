from __future__ import annotations

import random

import pytest

from engine import Card, full_deck, parse_cards
from external_research_world_sampler import AUTHORITY, sample_physical_world
from strategic_cfr import sample_deal_plan


def test_sampler_conserves_one_shared_54_card_world() -> None:
    known = parse_cards("Ac Kd Qh Js Tc 2c 3c")
    world = sample_physical_world(
        known_cards=known,
        zone_sizes=(
            ("p0_hidden_discards", 4),
            ("p1_hidden_discards", 4),
            ("p0_future", 12),
            ("p1_future", 12),
        ),
        seed=2026082801,
    )
    assert world.authority == AUTHORITY
    all_cards = world.all_cards()
    assert len(all_cards) == 54
    assert len(set(all_cards)) == 54
    assert set(all_cards) == set(full_deck(2))

    zones = [set(zone.cards) for zone in world.zones]
    for i in range(len(zones)):
        for j in range(i + 1, len(zones)):
            assert zones[i].isdisjoint(zones[j])
    assert set(known).isdisjoint(set().union(*zones))


def test_sampler_is_deterministic_for_same_seed_and_inputs() -> None:
    known = parse_cards("Ac Kd Qh Js Tc")
    kwargs = dict(
        known_cards=known,
        zone_sizes=(("p0", 9), ("p1", 9), ("opp_discard", 4)),
    )
    a = sample_physical_world(**kwargs, seed="world-seed")
    b = sample_physical_world(**kwargs, seed="world-seed")
    c = sample_physical_world(**kwargs, seed="other-seed")
    assert a == b
    assert a != c


def test_sampler_rejects_duplicate_known_cards_duplicate_zones_and_oversubscription() -> None:
    ac = Card.parse("Ac")
    with pytest.raises(ValueError, match="duplicate physical"):
        sample_physical_world(known_cards=(ac, ac), zone_sizes=(), seed=1)
    with pytest.raises(ValueError, match="names must be unique"):
        sample_physical_world(known_cards=(), zone_sizes=(("x", 1), ("x", 1)), seed=1)
    with pytest.raises(ValueError, match="exceeds remaining"):
        sample_physical_world(known_cards=(), zone_sizes=(("x", 55),), seed=1)


def test_current_hu_training_deal_plan_also_conserves_a_single_shared_world() -> None:
    # DeepOFC's strategic CFR samples a complete 34-card HU hand from one
    # shuffled target deck.  This is the correct physical-world pattern.
    for seed in (1, 2, 3, 20260828):
        plan = sample_deal_plan(random.Random(seed))
        dealt = plan.dealt_cards()
        assert len(dealt) == 34
        assert len(set(dealt)) == 34
        assert all(card in set(full_deck(2)) for card in dealt)


def _model_external_split_sampling_antipattern(deck: tuple[Card, ...], k0: int, k1: int):
    """Model the audited `deck.select()`-twice-without-consumption pattern.

    neery1218/OFCSolver samples hero completion from the current deck, then
    samples the opponent completion from the same undepleted Deck object.  Two
    individually legal samples therefore need not form one legal joint world.
    The deterministic construction below makes that logical defect explicit.
    """
    hero_future = tuple(deck[:k0])
    opponent_future = tuple(deck[:k1])
    return hero_future, opponent_future


def test_reject_split_future_sampling_without_shared_consumption() -> None:
    deck = tuple(full_deck(2))
    hero, opponent = _model_external_split_sampling_antipattern(deck, 9, 9)
    assert set(hero) & set(opponent)

    world = sample_physical_world(
        known_cards=(),
        zone_sizes=(("hero_future", 9), ("opponent_future", 9)),
        seed=7,
    )
    assert set(world.zone("hero_future")).isdisjoint(world.zone("opponent_future"))
