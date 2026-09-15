import unittest
from datetime import datetime, timedelta

from analysis.metrics import calculate_metrics
from engine.backtest import Trade


def make_trade(
    pnl,
    day,
):
    start = datetime(2026, 1, 1) + timedelta(days=day)

    return Trade(
        direction="long",
        entry_time=start,
        entry_price=100.0,
        exit_time=start + timedelta(hours=1),
        exit_price=100.0,
        size=1.0,
        pnl=pnl,
        exit_reason="test",
        strategy_reason="test",
    )


class TestPerformanceMetrics(unittest.TestCase):

    def test_basic_metrics(self):
        trades = [
            make_trade(100.0, 0),
            make_trade(-50.0, 1),
            make_trade(50.0, 2),
        ]

        metrics = calculate_metrics(
            starting_equity=10_000.0,
            trades=trades,
        )

        self.assertEqual(metrics.trade_count, 3)
        self.assertEqual(metrics.winning_trades, 2)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertEqual(metrics.breakeven_trades, 0)

        self.assertAlmostEqual(
            metrics.net_pnl,
            100.0,
        )

        self.assertAlmostEqual(
            metrics.ending_equity,
            10_100.0,
        )

        self.assertAlmostEqual(
            metrics.return_pct,
            1.0,
        )

        self.assertAlmostEqual(
            metrics.win_rate_pct,
            66.6666666667,
            places=6,
        )

    def test_profit_factor(self):
        trades = [
            make_trade(200.0, 0),
            make_trade(100.0, 1),
            make_trade(-100.0, 2),
        ]

        metrics = calculate_metrics(
            10_000.0,
            trades,
        )

        self.assertAlmostEqual(
            metrics.gross_profit,
            300.0,
        )

        self.assertAlmostEqual(
            metrics.gross_loss,
            100.0,
        )

        self.assertAlmostEqual(
            metrics.profit_factor,
            3.0,
        )

    def test_drawdown(self):
        trades = [
            make_trade(100.0, 0),
            make_trade(-200.0, 1),
            make_trade(50.0, 2),
        ]

        metrics = calculate_metrics(
            10_000.0,
            trades,
        )

        # Equity:
        # 10,000 → 10,100 → 9,900 → 9,950
        #
        # Peak = 10,100
        # Max DD = 200
        self.assertAlmostEqual(
            metrics.max_drawdown,
            200.0,
        )

        self.assertAlmostEqual(
            metrics.max_drawdown_pct,
            200.0 / 10_100.0 * 100.0,
        )

    def test_expectancy_equals_average_trade(self):
        trades = [
            make_trade(100.0, 0),
            make_trade(-50.0, 1),
            make_trade(-25.0, 2),
        ]

        metrics = calculate_metrics(
            10_000.0,
            trades,
        )

        self.assertAlmostEqual(
            metrics.expectancy,
            25.0 / 3.0,
        )

    def test_no_trades(self):
        metrics = calculate_metrics(
            10_000.0,
            [],
        )

        self.assertEqual(metrics.trade_count, 0)
        self.assertEqual(metrics.winning_trades, 0)
        self.assertEqual(metrics.losing_trades, 0)
        self.assertEqual(metrics.win_rate_pct, 0.0)
        self.assertEqual(metrics.net_pnl, 0.0)
        self.assertEqual(metrics.max_drawdown, 0.0)
        self.assertEqual(metrics.profit_factor, 0.0)

    def test_invalid_starting_equity(self):
        with self.assertRaises(ValueError):
            calculate_metrics(
                0.0,
                [],
            )


if __name__ == "__main__":
    unittest.main()


class TestTradeRMultiple(unittest.TestCase):

    def test_positive_r_multiple(self):
        trade = make_trade(200.0, 0)
        trade.initial_risk = 100.0

        self.assertAlmostEqual(
            trade.r_multiple,
            2.0,
        )

    def test_negative_r_multiple(self):
        trade = make_trade(-50.0, 0)
        trade.initial_risk = 100.0

        self.assertAlmostEqual(
            trade.r_multiple,
            -0.5,
        )

    def test_zero_risk_returns_zero(self):
        trade = make_trade(100.0, 0)

        self.assertEqual(
            trade.r_multiple,
            0.0,
        )


class TestEquitySequence(unittest.TestCase):
    def test_drawdown_tracks_high_water_mark_across_recovery(self):
        trades = [
            make_trade(100.0, 0),
            make_trade(-200.0, 1),
            make_trade(300.0, 2),
            make_trade(-50.0, 3),
        ]

        metrics = calculate_metrics(
            starting_equity=10_000.0,
            trades=trades,
        )

        # Equity:
        # 10,000 -> 10,100 -> 9,900 -> 10,200 -> 10,150
        #
        # Maximum drawdown occurs from 10,100 to 9,900.
        self.assertAlmostEqual(
            metrics.max_drawdown,
            200.0,
        )

        self.assertAlmostEqual(
            metrics.max_drawdown_pct,
            200.0 / 10_100.0 * 100.0,
        )

        self.assertAlmostEqual(
            metrics.ending_equity,
            10_150.0,
        )

        self.assertAlmostEqual(
            metrics.net_pnl,
            150.0,
        )

    def test_new_high_resets_drawdown_but_not_maximum_drawdown(self):
        trades = [
            make_trade(500.0, 0),
            make_trade(-100.0, 1),
            make_trade(700.0, 2),
            make_trade(-50.0, 3),
        ]

        metrics = calculate_metrics(
            starting_equity=10_000.0,
            trades=trades,
        )

        # Equity:
        # 10,000 -> 10,500 -> 10,400 -> 11,100 -> 11,050
        #
        # First DD = 100.
        # Second DD = 50.
        # Maximum remains 100.
        self.assertAlmostEqual(
            metrics.max_drawdown,
            100.0,
        )

        self.assertAlmostEqual(
            metrics.max_drawdown_pct,
            100.0 / 10_500.0 * 100.0,
        )

        self.assertAlmostEqual(
            metrics.ending_equity,
            11_050.0,
        )

    def test_breakeven_trade_does_not_count_as_win_or_loss(self):
        trades = [
            make_trade(100.0, 0),
            make_trade(0.0, 1),
            make_trade(-50.0, 2),
        ]

        metrics = calculate_metrics(
            starting_equity=10_000.0,
            trades=trades,
        )

        self.assertEqual(
            metrics.winning_trades,
            1,
        )

        self.assertEqual(
            metrics.losing_trades,
            1,
        )

        self.assertEqual(
            metrics.breakeven_trades,
            1,
        )

        self.assertAlmostEqual(
            metrics.win_rate_pct,
            1.0 / 3.0 * 100.0,
        )

        self.assertAlmostEqual(
            metrics.net_pnl,
            50.0,
        )
