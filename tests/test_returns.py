import unittest
from engine.backtest import EquityPoint
from datetime import datetime, timedelta

from research.returns import (
    annualized_return,
    find_time_gaps,
    mtm_equity_curve,
    PeriodicMetricConfig,
    periodic_returns,
    periodic_sharpe,
    periodic_sortino,
    periods_per_year,
    sample_mtm_equity,
    simple_returns,
    time_weighted_return,
)


class TestSimpleReturns(unittest.TestCase):
    def test_simple_returns(self):
        result = simple_returns(
            [100.0, 110.0, 105.0]
        )

        self.assertAlmostEqual(
            result[0],
            0.10,
        )

        self.assertAlmostEqual(
            result[1],
            -5.0 / 110.0,
        )

    def test_single_equity_point(self):
        self.assertEqual(
            simple_returns([100.0]),
            [],
        )

    def test_empty_equity(self):
        self.assertEqual(
            simple_returns([]),
            [],
        )

    def test_non_positive_previous_equity(self):
        with self.assertRaises(ValueError):
            simple_returns([100.0, 0.0, 10.0])


class TestTimeWeightedReturn(unittest.TestCase):
    def test_total_return(self):
        self.assertAlmostEqual(
            time_weighted_return(
                [10000.0, 10500.0]
            ),
            0.05,
        )

    def test_insufficient_data(self):
        self.assertEqual(
            time_weighted_return([10000.0]),
            0.0,
        )


class TestAnnualizedReturn(unittest.TestCase):
    def test_one_year_return(self):
        start = datetime(2025, 1, 1)
        end = datetime(2026, 1, 1)

        result = annualized_return(
            [10000.0, 11000.0],
            [start, end],
        )

        self.assertAlmostEqual(
            result,
            0.10,
            places=3,
        )

    def test_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            annualized_return(
                [100.0, 110.0],
                [datetime(2025, 1, 1)],
            )

    def test_zero_elapsed_time(self):
        timestamp = datetime(2025, 1, 1)

        with self.assertRaises(ValueError):
            annualized_return(
                [100.0, 110.0],
                [timestamp, timestamp],
            )


if __name__ == "__main__":
    unittest.main()


class TestMTMEquityCurve(unittest.TestCase):
    def test_extracts_mark_to_market_equity(self):

        points = [
            EquityPoint(
                time=datetime(2025, 1, 1),
                equity=10000.0,
                trade_pnl=0.0,
                cumulative_pnl=0.0,
                mark_to_market_equity=10000.0,
            ),
            EquityPoint(
                time=datetime(2025, 1, 2),
                equity=9999.0,
                trade_pnl=0.0,
                cumulative_pnl=-1.0,
                mark_to_market_equity=10100.0,
            ),
        ]

        self.assertEqual(
            mtm_equity_curve(points),
            [10000.0, 10100.0],
        )


class TestPeriodicMTMReturns(unittest.TestCase):
    def _point(self, minute, equity):
        return EquityPoint(
            time=datetime(2026, 1, 1, 0, minute),
            equity=equity,
            trade_pnl=0.0,
            cumulative_pnl=equity - 10000.0,
            mark_to_market_equity=equity,
        )

    def test_fixed_interval_sampling_uses_timestamps(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10050.0),
            self._point(2, 10100.0),
            self._point(3, 10200.0),
            self._point(4, 10300.0),
        ]

        timestamps, equity = sample_mtm_equity(points, interval_seconds=120)

        self.assertEqual(
            timestamps,
            [
                datetime(2026, 1, 1, 0, 0),
                datetime(2026, 1, 1, 0, 2),
                datetime(2026, 1, 1, 0, 4),
            ],
        )
        self.assertEqual(equity, [10000.0, 10100.0, 10300.0])

    def test_sampling_uses_first_observation_at_or_after_target(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10020.0),
            self._point(3, 10100.0),
            self._point(4, 10200.0),
        ]

        timestamps, equity = sample_mtm_equity(points, interval_seconds=120)

        self.assertEqual(
            timestamps,
            [
                datetime(2026, 1, 1, 0, 0),
                datetime(2026, 1, 1, 0, 3),
                datetime(2026, 1, 1, 0, 4),
            ],
        )
        self.assertEqual(equity, [10000.0, 10100.0, 10200.0])

    def test_periodic_returns_are_based_on_sampled_equity(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10050.0),
            self._point(2, 10100.0),
            self._point(4, 10300.0),
        ]

        timestamps, returns = periodic_returns(
            points,
            interval_seconds=120,
        )

        self.assertEqual(
            timestamps,
            [
                datetime(2026, 1, 1, 0, 2),
                datetime(2026, 1, 1, 0, 4),
            ],
        )
        self.assertAlmostEqual(returns[0], 0.01)
        self.assertAlmostEqual(returns[1], (10300.0 - 10100.0) / 10100.0)

    def test_invalid_interval_is_rejected(self):
        points = [self._point(0, 10000.0)]

        with self.assertRaises(ValueError):
            sample_mtm_equity(points, interval_seconds=0)

        with self.assertRaises(ValueError):
            periodic_returns(points, interval_seconds=-60)


class TestTimeGapDetection(unittest.TestCase):
    def test_no_gap_for_regular_series(self):
        timestamps = [
            datetime(2026, 1, 1, 0, 0),
            datetime(2026, 1, 1, 1, 0),
            datetime(2026, 1, 1, 2, 0),
        ]

        self.assertEqual(
            find_time_gaps(timestamps, expected_interval_seconds=3600),
            [],
        )

    def test_detects_large_gap(self):
        timestamps = [
            datetime(2026, 1, 1, 0, 0),
            datetime(2026, 1, 1, 1, 0),
            datetime(2026, 1, 1, 5, 0),
        ]

        gaps = find_time_gaps(
            timestamps,
            expected_interval_seconds=3600,
        )

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0][0], datetime(2026, 1, 1, 1, 0))
        self.assertEqual(gaps[0][1], datetime(2026, 1, 1, 5, 0))
        self.assertEqual(gaps[0][2], 14400.0)

    def test_tolerance_allows_small_irregularity(self):
        timestamps = [
            datetime(2026, 1, 1, 0, 0),
            datetime(2026, 1, 1, 1, 0),
            datetime(2026, 1, 1, 2, 20),
        ]

        gaps = find_time_gaps(
            timestamps,
            expected_interval_seconds=3600,
            tolerance=1.5,
        )

        self.assertEqual(gaps, [])

    def test_rejects_non_increasing_timestamps(self):
        timestamps = [
            datetime(2026, 1, 1, 1, 0),
            datetime(2026, 1, 1, 0, 0),
        ]

        with self.assertRaises(ValueError):
            find_time_gaps(
                timestamps,
                expected_interval_seconds=3600,
            )

    def test_invalid_interval(self):
        with self.assertRaises(ValueError):
            find_time_gaps([], expected_interval_seconds=0)

    def test_invalid_tolerance(self):
        with self.assertRaises(ValueError):
            find_time_gaps([], expected_interval_seconds=3600, tolerance=0.5)



class TestPeriodicRiskMetrics(unittest.TestCase):
    def _point(self, hour, equity):
        return EquityPoint(
            time=datetime(2026, 1, 1, hour, 0),
            equity=equity,
            trade_pnl=0.0,
            cumulative_pnl=equity - 10000.0,
            mark_to_market_equity=equity,
        )

    def test_periods_per_year(self):
        self.assertAlmostEqual(
            periods_per_year(86400),
            365.25,
        )

    def test_invalid_periods_per_year(self):
        with self.assertRaises(ValueError):
            periods_per_year(0)

    def test_periodic_metric_config_rejects_nonpositive_interval(self):
        with self.assertRaises(ValueError):
            PeriodicMetricConfig(interval_seconds=0)

        with self.assertRaises(ValueError):
            PeriodicMetricConfig(interval_seconds=-60)

    def test_periodic_metric_config_rejects_gap_tolerance_below_one(self):
        with self.assertRaises(ValueError):
            PeriodicMetricConfig(
                interval_seconds=3600,
                gap_tolerance=0.99,
            )

    def test_periodic_sharpe_accepts_config(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10100.0),
            self._point(2, 10050.0),
            self._point(3, 10200.0),
            self._point(4, 10150.0),
        ]
        config = PeriodicMetricConfig(
            interval_seconds=3600,
            gap_tolerance=1.5,
        )

        value = periodic_sharpe(points, config=config)

        self.assertNotEqual(value, 0.0)

    def test_periodic_sortino_accepts_config(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10100.0),
            self._point(2, 10050.0),
            self._point(3, 10200.0),
            self._point(4, 10150.0),
        ]
        config = PeriodicMetricConfig(
            interval_seconds=3600,
            gap_tolerance=1.5,
        )

        value = periodic_sortino(points, config=config)

        self.assertNotEqual(value, 0.0)

    def test_periodic_metrics_reject_interval_and_config_together(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10100.0),
            self._point(2, 10050.0),
            self._point(3, 10200.0),
            self._point(4, 10150.0),
        ]
        config = PeriodicMetricConfig(interval_seconds=3600)

        with self.assertRaises(ValueError):
            periodic_sharpe(
                points,
                interval_seconds=3600,
                config=config,
            )

        with self.assertRaises(ValueError):
            periodic_sortino(
                points,
                interval_seconds=3600,
                config=config,
            )

    def test_periodic_sharpe_is_annualized(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10100.0),
            self._point(2, 10050.0),
            self._point(3, 10200.0),
            self._point(4, 10150.0),
        ]

        value = periodic_sharpe(points, interval_seconds=3600)

        self.assertNotEqual(value, 0.0)

    def test_periodic_sortino_is_annualized(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10100.0),
            self._point(2, 10050.0),
            self._point(3, 10200.0),
            self._point(4, 10150.0),
        ]

        value = periodic_sortino(points, interval_seconds=3600)

        self.assertNotEqual(value, 0.0)

    def test_insufficient_periodic_returns(self):
        points = [
            self._point(0, 10000.0),
            self._point(1, 10100.0),
        ]

        self.assertEqual(
            periodic_sharpe(points, interval_seconds=3600),
            0.0,
        )
        self.assertEqual(
            periodic_sortino(points, interval_seconds=3600),
            0.0,
        )
