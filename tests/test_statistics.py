import math
import unittest

from research.statistics import (
    bootstrap_mean_ci,
    downside_deviation,
    expectancy,
    max_drawdown,
    max_drawdown_pct,
    mean_value,
    median_value,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    standard_deviation,
    win_rate,
)


class TestBasicStatistics(unittest.TestCase):
    def test_mean(self):
        self.assertEqual(mean_value([1.0, 2.0, 3.0]), 2.0)

    def test_median(self):
        self.assertEqual(median_value([1.0, 3.0, 2.0]), 2.0)

    def test_standard_deviation(self):
        self.assertAlmostEqual(
            standard_deviation([1.0, 2.0, 3.0]),
            1.0,
        )

    def test_empty_values(self):
        self.assertEqual(mean_value([]), 0.0)
        self.assertEqual(median_value([]), 0.0)
        self.assertEqual(standard_deviation([]), 0.0)


class TestTradingStatistics(unittest.TestCase):
    def test_win_rate(self):
        self.assertAlmostEqual(
            win_rate([1.0, -1.0, 2.0, -0.5]),
            0.5,
        )

    def test_expectancy(self):
        self.assertAlmostEqual(
            expectancy([1.0, -0.5, 2.0, -1.0]),
            0.375,
        )

    def test_profit_factor(self):
        self.assertAlmostEqual(
            profit_factor([2.0, 1.0, -1.0, -0.5]),
            2.0,
        )

    def test_profit_factor_no_losses(self):
        self.assertEqual(
            profit_factor([1.0, 2.0]),
            math.inf,
        )

    def test_sharpe(self):
        values = [1.0, 2.0, 3.0, 4.0]
        expected = mean_value(values) / standard_deviation(values)

        self.assertAlmostEqual(
            sharpe_ratio(values),
            expected,
        )

    def test_annualized_sharpe(self):
        values = [1.0, 2.0, 3.0, 4.0]
        base = mean_value(values) / standard_deviation(values)

        self.assertAlmostEqual(
            sharpe_ratio(values, periods_per_year=4),
            base * 2.0,
        )

    def test_downside_deviation(self):
        values = [2.0, -1.0, 3.0, -2.0]

        expected = math.sqrt((1.0 + 4.0) / 4.0)

        self.assertAlmostEqual(
            downside_deviation(values),
            expected,
        )

    def test_sortino(self):
        values = [2.0, -1.0, 3.0, -2.0]

        expected = mean_value(values) / downside_deviation(values)

        self.assertAlmostEqual(
            sortino_ratio(values),
            expected,
        )


class TestDrawdownStatistics(unittest.TestCase):
    def test_max_drawdown(self):
        equity = [10000.0, 10500.0, 10200.0, 9800.0, 11000.0]

        self.assertAlmostEqual(
            max_drawdown(equity),
            700.0,
        )

    def test_max_drawdown_percentage(self):
        equity = [10000.0, 10500.0, 10200.0, 9800.0, 11000.0]

        self.assertAlmostEqual(
            max_drawdown_pct(equity),
            (700.0 / 10500.0) * 100.0,
        )

    def test_no_drawdown(self):
        equity = [10000.0, 10100.0, 10200.0]

        self.assertEqual(
            max_drawdown(equity),
            0.0,
        )


class TestBootstrap(unittest.TestCase):
    def test_bootstrap_is_deterministic(self):
        values = [1.0, 1.0, 1.0, 1.0]

        first = bootstrap_mean_ci(values, iterations=500)
        second = bootstrap_mean_ci(values, iterations=500)

        self.assertEqual(first, second)

    def test_bootstrap_constant_sample(self):
        result = bootstrap_mean_ci(
            [2.0, 2.0, 2.0],
            iterations=500,
        )

        self.assertEqual(result, (2.0, 2.0))

    def test_bootstrap_invalid_iterations(self):
        with self.assertRaises(ValueError):
            bootstrap_mean_ci([1.0, 2.0], iterations=0)

    def test_bootstrap_invalid_confidence(self):
        with self.assertRaises(ValueError):
            bootstrap_mean_ci([1.0, 2.0], confidence=1.0)


if __name__ == "__main__":
    unittest.main()


class TestAnnualizedSortino(unittest.TestCase):
    def test_annualized_sortino(self):
        values = [2.0, -1.0, 3.0, -2.0]

        base = mean_value(values) / downside_deviation(values)

        self.assertAlmostEqual(
            sortino_ratio(values, periods_per_year=4),
            base * 2.0,
        )

    def test_invalid_periods_per_year(self):
        with self.assertRaises(ValueError):
            sortino_ratio([1.0, -1.0], periods_per_year=0)
