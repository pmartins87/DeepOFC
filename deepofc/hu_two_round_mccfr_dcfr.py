from __future__ import annotations

import math

from .actions import NormalPlacementAction
from .hu_two_round import HUTwoRoundSubgame, TwoRoundInfoSet
from .hu_two_round_mccfr import TwoRoundExternalSamplingMCCFR


class TwoRoundExternalSamplingLazyDCFR(TwoRoundExternalSamplingMCCFR):
    """External-sampling MCCFR with lazy DCFR-style regret discounting.

    This is an empirical R6 candidate, not a claim that the full-tree DCFR
    convergence theorem transfers unchanged to sampled updates.

    Full-tree DCFR discounts all *existing* regrets at iteration t before adding
    iteration-t regret deltas. A sampled implementation cannot scan every
    infoset each iteration without losing the point of sampling. We therefore
    store the last discount iteration for every infoset and apply all skipped
    multiplicative factors exactly when that infoset is next read or updated.

    Between regret updates an action regret cannot change sign, so the positive
    and negative DCFR factors can be collapsed safely over the skipped interval.
    Regret-matching behavior is also unchanged by those skipped discounts alone:
    all positive regrets receive the same factor and negative regrets remain
    irrelevant to the current positive-regret distribution.
    """

    def __init__(
        self,
        game: HUTwoRoundSubgame,
        *,
        seed: int = 1,
        alpha: float = 1.5,
        beta: float = 0.0,
    ) -> None:
        super().__init__(game, seed=seed)
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.last_discounted = {info: 0 for info in game.info_actions}
        # Prefix log-products: prefix[k] = log(product of factors 1..k).
        # They are extended only as training advances and make an arbitrarily
        # long lazy gap O(1) rather than O(gap).
        self._positive_log_prefix = [0.0]
        self._negative_log_prefix = [0.0]

    @staticmethod
    def _factor(iteration: int, exponent: float) -> float:
        if iteration <= 0:
            raise ValueError("DCFR discount iteration must be positive")
        power = float(iteration) ** exponent
        return power / (power + 1.0)

    def _ensure_prefix(self, iteration: int) -> None:
        while len(self._positive_log_prefix) <= iteration:
            k = len(self._positive_log_prefix)
            pos = self._factor(k, self.alpha)
            neg = self._factor(k, self.beta)
            self._positive_log_prefix.append(
                self._positive_log_prefix[-1] + math.log(pos)
            )
            self._negative_log_prefix.append(
                self._negative_log_prefix[-1] + math.log(neg)
            )

    def _collapsed_factor(self, start: int, end: int, *, positive: bool) -> float:
        """Product of DCFR factors for integer iterations start..end inclusive."""
        if end < start:
            return 1.0
        if start <= 0:
            raise ValueError("discount interval must start at iteration >= 1")
        self._ensure_prefix(end)
        prefix = self._positive_log_prefix if positive else self._negative_log_prefix
        log_product = prefix[end] - prefix[start - 1]
        # exp underflow to zero is the correct floating-point limit for regrets
        # that have been halved thousands of times without a new update.
        return math.exp(log_product)

    def _discount_to(self, info: TwoRoundInfoSet, target_iteration: int) -> None:
        last = self.last_discounted[info]
        if target_iteration <= last:
            return
        start = last + 1
        pos_factor = self._collapsed_factor(start, target_iteration, positive=True)
        neg_factor = self._collapsed_factor(start, target_iteration, positive=False)
        values = self.regrets[info]
        for action, old in tuple(values.items()):
            values[action] = old * (pos_factor if old >= 0.0 else neg_factor)
        self.last_discounted[info] = target_iteration

    def _distribution(self, info: TwoRoundInfoSet) -> dict[NormalPlacementAction, float]:
        # At the start of global iteration t, self.iteration == t-1. Full-tree
        # DCFR has already applied discounts through t-1, so lazily catch up
        # before this infoset participates in the sampled traversal.
        self._discount_to(info, self.iteration)
        return super()._distribution(info)

    def step(self) -> None:
        t = self.iteration + 1
        delta: dict[TwoRoundInfoSet, dict[NormalPlacementAction, float]] = {}

        # Both traversals see the same pre-update strategy, matching the base
        # external-sampling simultaneous-update convention.
        self._sampled_traversal(0, delta)
        self._sampled_traversal(1, delta)

        for info, values in delta.items():
            # Iteration t was played using the pre-t-discount behavior. Credit
            # that exact local interval before changing regrets.
            self._flush_local_strategy_used_through(info, t)

            # Full-tree DCFR now discounts the existing cumulative regrets for
            # iteration t, then adds iteration-t regret increments.
            self._discount_to(info, t)
            regrets = self.regrets[info]
            for action, increment in values.items():
                regrets[action] += increment
            self.local_active_since[info] = t + 1

        self.iteration = t

    def current_profile(self):
        # Reading the final current profile must reflect every completed global
        # DCFR discount even for infosets not sampled recently.
        return {info: self._distribution(info) for info in self.game.info_actions}
