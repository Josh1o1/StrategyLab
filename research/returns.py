from __future__ import annotations

from datetime import datetime
from typing import Sequence

from dataclasses import dataclass


@dataclass(frozen=True)
class PeriodicMetricConfig:
    """Configuration for fixed-frequency time-series risk metrics."""

    interval_seconds: float
    gap_tolerance: float = 1.5

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if self.gap_tolerance < 1.0:
            raise ValueError("gap_tolerance must be at least 1.0")



def simple_returns(equity: Sequence[float]) -> list[float]:
    """
    Convert an equity series into simple period returns.

    Example:
        [10000, 10100, 10050]
        -> [0.01, -0.004950495...]
    """
    if len(equity) < 2:
        return []

    returns: list[float] = []

    for previous, current in zip(equity, equity[1:]):
        if previous <= 0:
            raise ValueError(
                "Equity must remain positive to calculate returns"
            )

        returns.append((current - previous) / previous)

    return returns


def time_weighted_return(
    equity: Sequence[float],
) -> float:
    """
    Total simple return from the first to last equity observation.
    """
    if len(equity) < 2:
        return 0.0

    starting = equity[0]

    if starting <= 0:
        raise ValueError("Starting equity must be positive")

    return (equity[-1] - starting) / starting



def sample_mtm_equity(
    equity_points,
    interval_seconds: float,
) -> tuple[list[datetime], list[float]]:
    """
    Sample bar-by-bar MTM equity at a fixed elapsed-time interval.

    The first observation is always retained. Subsequent observations are
    taken at the first available timestamp at or after each target interval.

    This deliberately uses timestamps rather than bar counts so statistical
    frequency is independent of the strategy's chart timeframe.
    """
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")

    if not equity_points:
        return [], []

    timestamps = [point.time for point in equity_points]
    equity = mtm_equity_curve(equity_points)

    sampled_times = [timestamps[0]]
    sampled_equity = [equity[0]]

    next_target = timestamps[0].timestamp() + interval_seconds

    for timestamp, value in zip(timestamps[1:], equity[1:]):
        if timestamp.timestamp() >= next_target:
            sampled_times.append(timestamp)
            sampled_equity.append(value)

            while next_target <= timestamp.timestamp():
                next_target += interval_seconds

    return sampled_times, sampled_equity



def find_time_gaps(
    timestamps: Sequence[datetime],
    expected_interval_seconds: float,
    *,
    tolerance: float = 1.5,
) -> list[tuple[datetime, datetime, float]]:
    """Find timestamp gaps that materially exceed the expected interval.

    Returns tuples of:
        (previous_timestamp, current_timestamp, gap_seconds)

    A tolerance above 1.0 allows small irregularities without flagging them.
    The timestamps must be strictly increasing.
    """
    if expected_interval_seconds <= 0:
        raise ValueError("expected_interval_seconds must be positive")

    if tolerance < 1.0:
        raise ValueError("tolerance must be at least 1.0")

    if len(timestamps) < 2:
        return []

    gaps: list[tuple[datetime, datetime, float]] = []
    threshold = expected_interval_seconds * tolerance

    previous = timestamps[0]

    for current in timestamps[1:]:
        gap_seconds = (current - previous).total_seconds()

        if gap_seconds <= 0:
            raise ValueError("timestamps must be strictly increasing")

        if gap_seconds > threshold:
            gaps.append((previous, current, gap_seconds))

        previous = current

    return gaps


def periodic_returns(
    equity_points,
    interval_seconds: float,
) -> tuple[list[datetime], list[float]]:
    """
    Return fixed-frequency simple returns from MTM equity observations.

    Returns the timestamps associated with the ending observation of each
    sampled return period.
    """
    timestamps, equity = sample_mtm_equity(
        equity_points,
        interval_seconds,
    )

    return timestamps[1:], simple_returns(equity)



def periods_per_year(interval_seconds: float) -> float:
    """Return the number of fixed-length periods in a 365.25-day year."""
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")

    seconds_per_year = 365.25 * 24 * 60 * 60
    return seconds_per_year / interval_seconds


def periodic_sharpe(
    equity_points,
    interval_seconds: float | None = None,
    *,
    gap_tolerance: float = 1.5,
    config: PeriodicMetricConfig | None = None,
) -> float:
    """Calculate annualized Sharpe from fixed-frequency MTM returns."""

    from research.statistics import sharpe_ratio

    if config is not None:
        if interval_seconds is not None:
            raise ValueError(
                "pass either interval_seconds or config, not both"
            )
        interval_seconds = config.interval_seconds
        gap_tolerance = config.gap_tolerance

    if interval_seconds is None:
        raise ValueError(
            "interval_seconds or config is required"
        )

    gaps = find_time_gaps(
        [point.time for point in equity_points],
        interval_seconds,
        tolerance=gap_tolerance,
    )

    if gaps:
        return 0.0

    returns = periodic_returns(
        equity_points,
        interval_seconds,
    )[1]

    if len(returns) < 2:
        return 0.0

    return sharpe_ratio(
        returns,
        periods_per_year=periods_per_year(interval_seconds),
    )

def periodic_sortino(
    equity_points,
    interval_seconds: float | None = None,
    *,
    gap_tolerance: float = 1.5,
    config: PeriodicMetricConfig | None = None,
) -> float:
    """Calculate annualized Sortino from fixed-frequency MTM returns."""

    from research.statistics import sortino_ratio

    if config is not None:
        if interval_seconds is not None:
            raise ValueError(
                "pass either interval_seconds or config, not both"
            )
        interval_seconds = config.interval_seconds
        gap_tolerance = config.gap_tolerance

    if interval_seconds is None:
        raise ValueError(
            "interval_seconds or config is required"
        )

    gaps = find_time_gaps(
        [point.time for point in equity_points],
        interval_seconds,
        tolerance=gap_tolerance,
    )

    if gaps:
        return 0.0

    returns = periodic_returns(
        equity_points,
        interval_seconds,
    )[1]

    if len(returns) < 2:
        return 0.0

    return sortino_ratio(
        returns,
        periods_per_year=periods_per_year(interval_seconds),
    )

def annualized_return(
    equity: Sequence[float],
    timestamps: Sequence[datetime],
) -> float:
    """
    Annualized geometric return based on elapsed calendar time.
    """
    if len(equity) < 2:
        return 0.0

    if len(equity) != len(timestamps):
        raise ValueError(
            "equity and timestamps must have equal length"
        )

    starting = equity[0]
    ending = equity[-1]

    if starting <= 0 or ending <= 0:
        raise ValueError(
            "Equity must remain positive"
        )

    elapsed_seconds = (
        timestamps[-1] - timestamps[0]
    ).total_seconds()

    if elapsed_seconds <= 0:
        raise ValueError(
            "timestamps must span positive time"
        )

    years = elapsed_seconds / (365.25 * 24 * 60 * 60)

    if years <= 0:
        return 0.0

    return (ending / starting) ** (1.0 / years) - 1.0


def mtm_equity_curve(equity_points) -> list[float]:
    """
    Extract mark-to-market equity from BacktestEngine equity observations.

    The returned series contains one MTM equity value per processed bar.
    """
    return [
        point.mark_to_market_equity
        for point in equity_points
    ]
