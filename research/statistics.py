from __future__ import annotations

import math
import random
from statistics import mean, median, stdev
from typing import Sequence


def mean_value(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return mean(values)


def median_value(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return median(values)


def standard_deviation(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return stdev(values)


def win_rate(values: Sequence[float]) -> float:
    if not values:
        return 0.0

    wins = sum(1 for value in values if value > 0)
    return wins / len(values)


def expectancy(values: Sequence[float]) -> float:
    return mean_value(values)


def profit_factor(values: Sequence[float]) -> float:
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = sum(-value for value in values if value < 0)

    if gross_loss == 0:
        if gross_profit > 0:
            return math.inf
        return 0.0

    return gross_profit / gross_loss


def sharpe_ratio(
    values: Sequence[float],
    periods_per_year: float | None = None,
) -> float:
    if len(values) < 2:
        return 0.0

    deviation = standard_deviation(values)

    if deviation == 0:
        return 0.0

    ratio = mean_value(values) / deviation

    if periods_per_year is not None:
        if periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")
        ratio *= math.sqrt(periods_per_year)

    return ratio


def downside_deviation(
    values: Sequence[float],
    target: float = 0.0,
) -> float:
    if not values:
        return 0.0

    squared = [
        (value - target) ** 2
        for value in values
        if value < target
    ]

    if not squared:
        return 0.0

    return math.sqrt(sum(squared) / len(values))


def sortino_ratio(
    values: Sequence[float],
    target: float = 0.0,
    periods_per_year: float | None = None,
) -> float:
    if not values:
        return 0.0

    downside = downside_deviation(values, target)

    if downside == 0:
        return 0.0

    ratio = (mean_value(values) - target) / downside

    if periods_per_year is not None:
        if periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")
        ratio *= math.sqrt(periods_per_year)

    return ratio

def max_drawdown(equity_curve: Sequence[float]) -> float:
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    maximum_drawdown = 0.0

    for equity in equity_curve:
        if equity > peak:
            peak = equity

        drawdown = peak - equity

        if drawdown > maximum_drawdown:
            maximum_drawdown = drawdown

    return maximum_drawdown


def max_drawdown_pct(equity_curve: Sequence[float]) -> float:
    if not equity_curve:
        return 0.0

    peak = equity_curve[0]
    maximum_drawdown = 0.0

    for equity in equity_curve:
        if equity > peak:
            peak = equity

        if peak <= 0:
            continue

        drawdown_pct = (peak - equity) / peak * 100.0

        if drawdown_pct > maximum_drawdown:
            maximum_drawdown = drawdown_pct

    return maximum_drawdown


def bootstrap_mean_ci(
    values: Sequence[float],
    iterations: int = 5000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)

    if iterations <= 0:
        raise ValueError("iterations must be positive")

    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    rng = random.Random(seed)
    n = len(values)

    samples = []

    for _ in range(iterations):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(mean(sample))

    samples.sort()

    alpha = 1.0 - confidence
    lower_index = int((alpha / 2.0) * iterations)
    upper_index = int((1.0 - alpha / 2.0) * iterations)

    upper_index = min(upper_index, iterations - 1)

    return samples[lower_index], samples[upper_index]
