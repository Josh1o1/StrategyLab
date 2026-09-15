import unittest
from datetime import datetime, timedelta

from engine.backtest import BacktestEngine
from engine.data import Bar
from engine.setup import TradeSetup
from strategies.test_strategy import TestLongStrategy


class TestTradeSetupContract(unittest.TestCase):

    def test_valid_long_setup(self):
        setup = TradeSetup(
            direction="long",
            entry=100,
            stop_loss=95,
            take_profit=110,
            reason="breakout",
        )

        self.assertEqual(setup.direction, "long")
        self.assertEqual(setup.entry_type, "market")
        self.assertEqual(setup.risk_distance, 5)
        self.assertEqual(setup.reward_distance, 10)
        self.assertEqual(setup.risk_reward, 2)

    def test_valid_short_setup(self):
        setup = TradeSetup(
            direction="short",
            entry=100,
            stop_loss=105,
            take_profit=90,
        )

        self.assertEqual(setup.risk_distance, 5)
        self.assertEqual(setup.reward_distance, 10)
        self.assertEqual(setup.risk_reward, 2)

    def test_long_stop_must_be_below_entry(self):
        with self.assertRaises(ValueError):
            TradeSetup(
                direction="long",
                entry=100,
                stop_loss=101,
            )

    def test_short_stop_must_be_above_entry(self):
        with self.assertRaises(ValueError):
            TradeSetup(
                direction="short",
                entry=100,
                stop_loss=99,
            )

    def test_long_target_must_be_above_entry(self):
        with self.assertRaises(ValueError):
            TradeSetup(
                direction="long",
                entry=100,
                stop_loss=95,
                take_profit=90,
            )

    def test_short_target_must_be_below_entry(self):
        with self.assertRaises(ValueError):
            TradeSetup(
                direction="short",
                entry=100,
                stop_loss=105,
                take_profit=110,
            )

    def test_limit_entry_type(self):
        setup = TradeSetup(
            direction="long",
            entry=100,
            stop_loss=95,
            take_profit=110,
            entry_type="limit",
        )

        self.assertEqual(
            setup.entry_type,
            "limit",
        )

    def test_stop_entry_type(self):
        setup = TradeSetup(
            direction="long",
            entry=100,
            stop_loss=95,
            take_profit=110,
            entry_type="stop",
        )

        self.assertEqual(
            setup.entry_type,
            "stop",
        )


class TestStrategy(unittest.TestCase):

    def test_strategy_returns_setup(self):
        bars = [
            Bar(
                datetime(2026, 1, 1),
                100,
                105,
                99,
                103,
            )
        ]

        strategy = TestLongStrategy()

        setup = strategy.generate_setup(
            bars,
            0,
        )

        self.assertIsNotNone(setup)
        self.assertEqual(
            setup.direction,
            "long",
        )
        self.assertEqual(
            setup.entry,
            103,
        )
        self.assertEqual(
            setup.stop_loss,
            101,
        )
        self.assertEqual(
            setup.take_profit,
            107,
        )


class TestStrategyExecution(unittest.TestCase):

    def test_market_setup_enters_next_bar_open(self):
        start = datetime(2026, 1, 1)

        bars = [
            Bar(
                start,
                100,
                104,
                99,
                103,
            ),
            Bar(
                start + timedelta(days=1),
                105,
                106,
                103,
                105,
            ),
            Bar(
                start + timedelta(days=2),
                103,
                104,
                100,
                101,
            ),
        ]

        strategy = TestLongStrategy()

        engine = BacktestEngine(
            starting_equity=10_000,
            risk_fraction=0.01,
        )

        result = engine.run_strategy(
            strategy,
            bars,
        )

        self.assertEqual(
            len(result.trades),
            1,
        )

        trade = result.trades[0]

        # Signal was generated on bar 0.
        # Actual market entry must be bar 1 open.
        self.assertEqual(
            trade.entry_time,
            bars[1].time,
        )

        self.assertEqual(
            trade.entry_price,
            bars[1].open,
        )

        self.assertEqual(
            trade.exit_reason,
            "stop",
        )

    def test_market_entry_cost_is_recorded_on_execution_bar(self):
        start = datetime(2026, 1, 1)

        bars = [
            Bar(
                start,
                100,
                104,
                99,
                103,
            ),
            Bar(
                start + timedelta(days=1),
                105,
                106,
                103,
                105,
            ),
            Bar(
                start + timedelta(days=2),
                103,
                104,
                100,
                101,
            ),
        ]

        from engine.costs import CostModel

        engine = BacktestEngine(
            starting_equity=10_000,
            risk_fraction=0.01,
            costs=CostModel(
                spread=1.0,
                slippage=0.0,
                commission_per_unit=0.0,
            ),
        )

        strategy = TestLongStrategy()

        result = engine.run_strategy(
            strategy,
            bars,
        )

        self.assertEqual(
            len(result.equity_curve),
            len(bars),
        )

        # Bar 0 generated the signal. No execution has occurred yet.
        self.assertAlmostEqual(
            result.equity_curve[0].equity,
            10_000.0,
            places=8,
        )

        # Bar 1 is the actual market-entry bar.
        # The entry cost must therefore first appear here.
        self.assertLess(
            result.equity_curve[1].equity,
            10_000.0,
        )

        self.assertEqual(
            result.equity_curve[0].time,
            bars[0].time,
        )

        self.assertEqual(
            result.equity_curve[1].time,
            bars[1].time,
        )

    def test_no_signal_means_no_trade(self):
        class NoTradeStrategy:
            def generate_setup(self, bars, index):
                return None

        bars = [
            Bar(
                datetime(2026, 1, 1),
                100,
                101,
                99,
                100,
            ),
            Bar(
                datetime(2026, 1, 2),
                100,
                102,
                98,
                101,
            ),
        ]

        engine = BacktestEngine()

        result = engine.run_strategy(
            NoTradeStrategy(),
            bars,
        )

        self.assertEqual(
            len(result.trades),
            0,
        )

        self.assertEqual(
            result.ending_equity,
            10_000,
        )


if __name__ == "__main__":
    unittest.main()


def test_mark_to_market_equity_includes_unrealized_pnl():
    from engine.backtest import BacktestEngine
    from engine.data import Bar

    bars = [
        Bar(
            time=0,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
        ),
        Bar(
            time=1,
            open=100.0,
            high=105.0,
            low=100.0,
            close=104.0,
        ),
        Bar(
            time=2,
            open=104.0,
            high=105.0,
            low=103.0,
            close=104.0,
        ),
    ]

    result = BacktestEngine(
        starting_equity=10_000.0,
        risk_fraction=0.01,
    ).run_strategy(TestLongStrategy(), bars)

    assert len(result.equity_curve) == len(bars)

    first = result.equity_curve[0]
    second = result.equity_curve[1]

    assert first.mark_to_market_equity == first.equity
    assert second.mark_to_market_equity > second.equity


def test_mark_to_market_equity_returns_to_realized_equity_after_exit():
    from engine.backtest import BacktestEngine
    from engine.data import Bar

    bars = [
        Bar(time=0, open=100.0, high=101.0, low=99.0, close=100.0),
        Bar(time=1, open=100.0, high=105.0, low=100.0, close=104.0),
        Bar(time=2, open=104.0, high=105.0, low=103.0, close=104.0),
    ]

    result = BacktestEngine(
        starting_equity=10_000.0,
        risk_fraction=0.01,
    ).run_strategy(TestLongStrategy(), bars)

    last = result.equity_curve[-1]

    if not result.trades:
        raise AssertionError("Expected TestLongStrategy to produce a trade")

    assert last.mark_to_market_equity == last.equity
