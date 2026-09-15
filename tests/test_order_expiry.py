import unittest
from datetime import datetime, timedelta

from engine.data import Bar
from engine.setup import TradeSetup
from engine.backtest import BacktestEngine


class LimitStrategy:
    def __init__(self, setup):
        self.setup = setup

    def generate_setup(self, bars, index):
        if index == 0:
            return self.setup
        return None


def make_bars():
    start = datetime(2026, 1, 1)

    return [
        Bar(start, 100, 105, 99, 104),
        Bar(start + timedelta(days=1), 104, 106, 103, 105),
        Bar(start + timedelta(days=2), 105, 107, 104, 106),
        Bar(start + timedelta(days=3), 106, 108, 105, 107),
    ]


class TestOrderExpiry(unittest.TestCase):

    def test_limit_order_expires(self):
        setup = TradeSetup(
            direction="long",
            entry=100,
            stop_loss=95,
            take_profit=110,
            entry_type="limit",
            max_bars=2,
        )

        result = BacktestEngine().run_strategy(
            LimitStrategy(setup),
            make_bars(),
        )

        self.assertEqual(len(result.trades), 0)

    def test_limit_order_can_trigger_before_expiry(self):
        bars = make_bars()

        # Bar 1 triggers the limit entry at 100.
        bars[1] = Bar(
            bars[1].time,
            104,
            106,
            99,
            105,
        )

        # Bar 2 subsequently hits the stop so the trade is closed.
        bars[2] = Bar(
            bars[2].time,
            105,
            107,
            94,
            106,
        )

        setup = TradeSetup(
            direction="long",
            entry=100,
            stop_loss=95,
            take_profit=110,
            entry_type="limit",
            max_bars=2,
        )

        result = BacktestEngine().run_strategy(
            LimitStrategy(setup),
            bars,
        )

        self.assertEqual(len(result.trades), 1)
        self.assertEqual(
            result.trades[0].entry_price,
            100,
        )
        self.assertEqual(
            result.trades[0].exit_reason,
            "stop",
        )

    def test_max_bars_must_be_positive(self):
        with self.assertRaises(ValueError):
            TradeSetup(
                direction="long",
                entry=100,
                stop_loss=95,
                take_profit=110,
                entry_type="limit",
                max_bars=0,
            )

    def test_none_means_no_expiry(self):
        setup = TradeSetup(
            direction="long",
            entry=100,
            stop_loss=95,
            take_profit=110,
            entry_type="limit",
            max_bars=None,
        )

        self.assertIsNone(setup.max_bars)


if __name__ == "__main__":
    unittest.main()
