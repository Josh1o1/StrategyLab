import unittest
from datetime import datetime, timedelta

from engine.backtest import BacktestEngine
from engine.costs import CostModel
from engine.data import Bar
from strategies.donchian import DonchianATRStrategy


def make_bars():
    start = datetime(2026, 1, 1)
    bars = []

    # Stable history.
    for i in range(20):
        bars.append(
            Bar(
                time=start + timedelta(hours=i),
                open=102.0,
                high=105.0,
                low=99.0,
                close=103.0,
            )
        )

    # Donchian breakout candle.
    bars.append(
        Bar(
            time=start + timedelta(hours=20),
            open=105.0,
            high=112.0,
            low=104.0,
            close=111.0,
        )
    )

    # Market entry occurs at open = 110.
    # The stop is hit on this same entry bar.
    bars.append(
        Bar(
            time=start + timedelta(hours=21),
            open=110.0,
            high=111.0,
            low=98.0,
            close=109.0,
        )
    )

    # Extra bar keeps the closed trade explicit.
    bars.append(
        Bar(
            time=start + timedelta(hours=22),
            open=109.0,
            high=110.0,
            low=108.0,
            close=109.0,
        )
    )

    return bars


class TestDonchianBacktest(unittest.TestCase):
    def test_breakout_to_stop_end_to_end(self):
        bars = make_bars()

        costs = CostModel(
            spread=0.1,
            slippage=0.0,
            commission_per_unit=0.0,
        )

        engine = BacktestEngine(
            starting_equity=10_000.0,
            risk_fraction=0.01,
            costs=costs,
        )

        strategy = DonchianATRStrategy(
            channel_period=20,
            atr_period=14,
            atr_multiplier=2.0,
        )

        result = engine.run_strategy(strategy, bars)

        self.assertEqual(len(result.trades), 1)

        trade = result.trades[0]

        self.assertEqual(trade.direction, "long")
        self.assertEqual(trade.entry_time, bars[21].time)
        self.assertEqual(trade.entry_price, 110.0)
        self.assertEqual(trade.exit_time, bars[21].time)
        self.assertEqual(trade.exit_reason, "stop")
        self.assertEqual(
            trade.strategy_reason,
            "donchian_long_20",
        )

        expected_stop = 98.57142857142857

        self.assertAlmostEqual(
            trade.exit_price,
            expected_stop,
            places=8,
        )

        expected_size = 100.0 / (110.0 - expected_stop)

        self.assertAlmostEqual(
            trade.size,
            expected_size,
            places=8,
        )

        expected_initial_risk = (
            (110.0 - expected_stop)
            * expected_size
        )

        self.assertAlmostEqual(
            trade.initial_risk,
            expected_initial_risk,
            places=8,
        )

        # Gross loss is exactly 1R.
        expected_gross_pnl = -100.0

        expected_entry_cost = (
            0.1 * expected_size
        )

        expected_exit_cost = (
            0.1 * expected_size
        )

        # Trade.pnl is the complete net result.
        expected_trade_pnl = (
            expected_gross_pnl
            - expected_entry_cost
            - expected_exit_cost
        )

        self.assertAlmostEqual(
            trade.gross_pnl,
            expected_gross_pnl,
            places=8,
        )

        self.assertAlmostEqual(
            trade.entry_cost,
            expected_entry_cost,
            places=8,
        )

        self.assertAlmostEqual(
            trade.exit_cost,
            expected_exit_cost,
            places=8,
        )

        self.assertAlmostEqual(
            trade.pnl,
            expected_trade_pnl,
            places=8,
        )

        self.assertAlmostEqual(
            trade.r_multiple,
            expected_trade_pnl / expected_initial_risk,
            places=8,
        )

        self.assertAlmostEqual(
            result.ending_equity,
            10_000.0 + expected_trade_pnl,
            places=8,
        )

        self.assertAlmostEqual(
            result.net_pnl,
            expected_trade_pnl,
            places=8,
        )


class TestTradeCostAccounting(unittest.TestCase):
    def test_trade_records_gross_and_both_costs(self):
        bars = make_bars()

        strategy = DonchianATRStrategy(
            channel_period=20,
            atr_period=14,
            atr_multiplier=2.0,
        )

        costs = CostModel(
            spread=0.1,
            slippage=0.0,
            commission_per_unit=0.0,
        )

        engine = BacktestEngine(
            starting_equity=10_000.0,
            risk_fraction=0.01,
            costs=costs,
        )

        result = engine.run_strategy(
            strategy,
            bars,
        )

        self.assertEqual(len(result.trades), 1)

        trade = result.trades[0]

        expected_size = 8.75
        expected_cost = 0.1 * expected_size

        self.assertAlmostEqual(
            trade.gross_pnl,
            -100.0,
            places=8,
        )

        self.assertAlmostEqual(
            trade.entry_cost,
            expected_cost,
            places=8,
        )

        self.assertAlmostEqual(
            trade.exit_cost,
            expected_cost,
            places=8,
        )

        self.assertAlmostEqual(
            trade.pnl,
            -100.0 - expected_cost - expected_cost,
            places=8,
        )

        self.assertAlmostEqual(
            result.net_pnl,
            trade.pnl,
            places=8,
        )


if __name__ == "__main__":
    unittest.main()


class TestEquityCurve(unittest.TestCase):
    def test_closed_trade_creates_equity_point(self):
        bars = make_bars()

        costs = CostModel(
            spread=0.1,
            slippage=0.0,
            commission_per_unit=0.0,
        )

        engine = BacktestEngine(
            starting_equity=10_000.0,
            risk_fraction=0.01,
            costs=costs,
        )

        strategy = DonchianATRStrategy(
            channel_period=20,
            atr_period=14,
            atr_multiplier=2.0,
        )

        result = engine.run_strategy(
            strategy,
            bars,
        )

        self.assertEqual(
            len(result.equity_curve),
            len(bars),
        )

        self.assertTrue(result.trades)

        trade = result.trades[0]

        matching_points = [
            point
            for point in result.equity_curve
            if point.time == trade.exit_time
        ]

        self.assertEqual(
            len(matching_points),
            1,
        )

        point = matching_points[0]

        self.assertAlmostEqual(
            point.equity,
            result.ending_equity,
            places=8,
        )

        self.assertAlmostEqual(
            point.trade_pnl,
            trade.pnl,
            places=8,
        )

        self.assertAlmostEqual(
            point.cumulative_pnl,
            result.net_pnl,
            places=8,
        )


class TestBarByBarEquityCurve(unittest.TestCase):
    def test_equity_curve_has_one_point_per_processed_bar(self):
        bars = make_bars()

        engine = BacktestEngine(
            starting_equity=10_000.0,
            risk_fraction=0.01,
        )

        strategy = DonchianATRStrategy(
            channel_period=2,
            atr_period=2,
            atr_multiplier=2.0,
        )

        result = engine.run_strategy(
            strategy,
            bars,
        )

        self.assertEqual(
            len(result.equity_curve),
            len(bars),
        )

        self.assertEqual(
            [point.time for point in result.equity_curve],
            [bar.time for bar in bars],
        )

    def test_equity_curve_ends_at_account_equity(self):
        bars = make_bars()

        engine = BacktestEngine(
            starting_equity=10_000.0,
            risk_fraction=0.01,
        )

        strategy = DonchianATRStrategy(
            channel_period=2,
            atr_period=2,
            atr_multiplier=2.0,
        )

        result = engine.run_strategy(
            strategy,
            bars,
        )

        self.assertAlmostEqual(
            result.equity_curve[-1].equity,
            result.ending_equity,
        )

    def test_trade_pnl_is_recorded_on_exit_bar(self):
        bars = make_bars()

        engine = BacktestEngine(
            starting_equity=10_000.0,
            risk_fraction=0.01,
        )

        strategy = DonchianATRStrategy(
            channel_period=20,
            atr_period=14,
            atr_multiplier=2.0,
        )

        result = engine.run_strategy(
            strategy,
            bars,
        )

        self.assertTrue(result.trades)

        trade = result.trades[0]

        matching_points = [
            point
            for point in result.equity_curve
            if point.time == trade.exit_time
        ]

        self.assertEqual(
            len(matching_points),
            1,
        )

        self.assertAlmostEqual(
            matching_points[0].trade_pnl,
            trade.pnl,
            places=8,
        )
