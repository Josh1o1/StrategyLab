from __future__ import annotations

from dataclasses import dataclass

from analysis.metrics import PerformanceMetrics, calculate_metrics
from engine.backtest import BacktestResult
from research.returns import (
    PeriodicMetricConfig,
    find_time_gaps,
    periodic_sharpe,
    periodic_sortino,
)
from research.statistics import (
    bootstrap_mean_ci,
    max_drawdown,
    max_drawdown_pct,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    win_rate,
)


@dataclass(frozen=True)
class ResearchReport:
    starting_equity: float
    ending_equity: float

    trade_count: int
    win_rate: float
    profit_factor: float
    expectancy: float
    average_r: float

    # Primary risk metrics: MTM time-series metrics.
    sharpe: float
    sortino: float

    # Diagnostic/legacy metrics: trade-level R metrics.
    trade_sharpe: float
    trade_sortino: float

    max_drawdown: float
    max_drawdown_pct: float

    mean_r_ci_lower: float
    mean_r_ci_upper: float

    @classmethod
    def from_backtest(
        cls,
        result: BacktestResult,
        interval_seconds: float | None = None,
        periodic_config: PeriodicMetricConfig | None = None,
    ) -> "ResearchReport":
        if periodic_config is not None:
            if interval_seconds is not None:
                raise ValueError(
                    "pass either interval_seconds or periodic_config, not both"
                )
            interval_seconds = periodic_config.interval_seconds
            gap_tolerance = periodic_config.gap_tolerance
        else:
            gap_tolerance = 1.5

        metrics: PerformanceMetrics = calculate_metrics(
            result.starting_equity,
            result.trades,
        )

        r_values = [
            trade.r_multiple
            for trade in result.trades
        ]

        equity_curve = [
            result.starting_equity,
            *[
                point.equity
                for point in result.equity_curve
            ],
        ]

        ci_lower, ci_upper = bootstrap_mean_ci(r_values)

        # Preserve trade-level statistics as diagnostics.
        trade_sharpe = sharpe_ratio(r_values)
        trade_sortino = sortino_ratio(r_values)

        # Primary risk metrics come from MTM equity sampled at a
        # fixed interval. Without enough observations, report zero.
        time_series_sharpe = 0.0
        time_series_sortino = 0.0

        points = result.equity_curve

        # Older/manual EquityPoint instances may not populate the
        # MTM field, whose historical default is 0.0. Fall back to
        # realized account equity in that case. Real backtest output
        # populates mark_to_market_equity explicitly.
        normalized_points = []

        for point in points:
            if point.mark_to_market_equity > 0:
                normalized_points.append(point)
            else:
                from engine.backtest import EquityPoint

                normalized_points.append(
                    EquityPoint(
                        time=point.time,
                        equity=point.equity,
                        trade_pnl=point.trade_pnl,
                        cumulative_pnl=point.cumulative_pnl,
                        mark_to_market_equity=point.equity,
                    )
                )

        if len(normalized_points) >= 3:
            timestamps = [
                point.time
                for point in normalized_points
            ]

            if interval_seconds is None:
                gaps = [
                    (current - previous).total_seconds()
                    for previous, current in zip(
                        timestamps,
                        timestamps[1:],
                    )
                ]

                positive_gaps = [
                    gap
                    for gap in gaps
                    if gap > 0
                ]

                if positive_gaps:
                    positive_gaps.sort()
                    interval_seconds = positive_gaps[
                        len(positive_gaps) // 2
                    ]

            if interval_seconds is not None:
                try:
                    gaps = find_time_gaps(
                    timestamps,
                    interval_seconds,
                    tolerance=gap_tolerance,
                )
                except ValueError:
                    gaps = [object()]

                if not gaps:
                    time_series_sharpe = periodic_sharpe(
                        normalized_points,
                        interval_seconds,
                        gap_tolerance=gap_tolerance,
                    )
                    time_series_sortino = periodic_sortino(
                        normalized_points,
                        interval_seconds,
                        gap_tolerance=gap_tolerance,
                    )

        return cls(
            starting_equity=result.starting_equity,
            ending_equity=result.ending_equity,

            trade_count=metrics.trade_count,
            win_rate=win_rate(r_values),
            profit_factor=profit_factor(r_values),
            expectancy=metrics.expectancy,
            average_r=(
                sum(r_values) / len(r_values)
                if r_values
                else 0.0
            ),

            sharpe=time_series_sharpe,
            sortino=time_series_sortino,

            trade_sharpe=trade_sharpe,
            trade_sortino=trade_sortino,

            max_drawdown=max_drawdown(equity_curve),
            max_drawdown_pct=max_drawdown_pct(equity_curve),

            mean_r_ci_lower=ci_lower,
            mean_r_ci_upper=ci_upper,
        )

    @property
    def net_pnl(self) -> float:
        return self.ending_equity - self.starting_equity

    @property
    def return_pct(self) -> float:
        if self.starting_equity <= 0:
            return 0.0

        return (
            self.net_pnl
            / self.starting_equity
            * 100.0
        )

    @property
    def mean_r_ci_excludes_zero(self) -> bool:
        return (
            self.mean_r_ci_lower > 0
            or self.mean_r_ci_upper < 0
        )
