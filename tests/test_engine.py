import unittest
from datetime import datetime, timedelta

from engine.costs import CostModel
from engine.data import Bar
from engine.execution import ExecutionSimulator
from engine.positions import Position


class TestBar(unittest.TestCase):

    def test_valid_bar(self):
        bar = Bar(
            datetime(2026, 1, 1),
            100,
            105,
            95,
            102,
        )

        self.assertEqual(bar.open, 100)
        self.assertEqual(bar.high, 105)
        self.assertEqual(bar.low, 95)
        self.assertEqual(bar.close, 102)

    def test_invalid_high(self):
        with self.assertRaises(ValueError):
            Bar(
                datetime(2026, 1, 1),
                100,
                99,
                95,
                98,
            )


class TestExecution(unittest.TestCase):

    def setUp(self):
        self.execution = ExecutionSimulator()

    def test_long_stop(self):
        position = Position(
            direction="long",
            entry_time=datetime(2026, 1, 1),
            entry_price=100,
            size=1,
            stop_loss=95,
            take_profit=110,
        )

        bar = Bar(
            datetime(2026, 1, 2),
            100,
            105,
            94,
            102,
        )

        result = self.execution.check_exit(
            position,
            bar,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.price, 95)
        self.assertEqual(result.reason, "stop")

    def test_long_target(self):
        position = Position(
            direction="long",
            entry_time=datetime(2026, 1, 1),
            entry_price=100,
            size=1,
            stop_loss=95,
            take_profit=110,
        )

        bar = Bar(
            datetime(2026, 1, 2),
            100,
            111,
            99,
            108,
        )

        result = self.execution.check_exit(
            position,
            bar,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.price, 110)
        self.assertEqual(
            result.reason,
            "take_profit",
        )

    def test_ambiguous_bar_is_stop_first(self):
        position = Position(
            direction="long",
            entry_time=datetime(2026, 1, 1),
            entry_price=100,
            size=1,
            stop_loss=95,
            take_profit=110,
        )

        bar = Bar(
            datetime(2026, 1, 2),
            100,
            111,
            94,
            105,
        )

        result = self.execution.check_exit(
            position,
            bar,
        )

        self.assertEqual(result.price, 95)
        self.assertEqual(result.reason, "stop")

    def test_short_stop(self):
        position = Position(
            direction="short",
            entry_time=datetime(2026, 1, 1),
            entry_price=100,
            size=1,
            stop_loss=105,
            take_profit=90,
        )

        bar = Bar(
            datetime(2026, 1, 2),
            100,
            106,
            95,
            98,
        )

        result = self.execution.check_exit(
            position,
            bar,
        )

        self.assertEqual(result.price, 105)
        self.assertEqual(result.reason, "stop")


class TestCosts(unittest.TestCase):

    def test_round_trip_cost(self):
        costs = CostModel(
            spread=0.1,
            slippage=0.05,
            commission_per_unit=0.02,
        )

        self.assertAlmostEqual(
            costs.round_trip_cost(10),
            3.4,
        )


if __name__ == "__main__":
    unittest.main()
