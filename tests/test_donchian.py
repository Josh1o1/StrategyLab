import unittest
from datetime import datetime, timedelta

from engine.data import Bar
from strategies.donchian import DonchianATRStrategy


def make_bars(count=25):
    bars = []
    start = datetime(2026, 1, 1)

    for i in range(count):
        base = 100.0 + i * 0.05

        bars.append(
            Bar(
                time=start + timedelta(hours=i),
                open=base,
                high=base + 5.0,
                low=base - 1.0,
                close=base + 2.0,
            )
        )

    return bars


class TestDonchianStrategy(unittest.TestCase):

    def test_no_signal_before_channel_history(self):
        bars = make_bars(25)

        strategy = DonchianATRStrategy(
            channel_period=20,
            atr_period=14,
            atr_multiplier=2.0,
        )

        setup = strategy.generate_setup(bars, 19)

        self.assertIsNone(setup)

    def test_long_breakout(self):
        bars = make_bars(25)

        bars[20] = Bar(
            time=bars[20].time,
            open=105.0,
            high=112.0,
            low=104.0,
            close=111.0,
        )

        strategy = DonchianATRStrategy(
            channel_period=20,
            atr_period=14,
            atr_multiplier=2.0,
        )

        setup = strategy.generate_setup(bars, 20)

        self.assertIsNotNone(setup)
        self.assertEqual(setup.direction, "long")
        self.assertEqual(setup.entry_type, "market")
        self.assertEqual(setup.entry, 111.0)
        self.assertLess(setup.stop_loss, setup.entry)

    def test_short_breakout(self):
        bars = make_bars(25)

        bars[20] = Bar(
            time=bars[20].time,
            open=100.0,
            high=101.0,
            low=88.0,
            close=89.0,
        )

        strategy = DonchianATRStrategy(
            channel_period=20,
            atr_period=14,
            atr_multiplier=2.0,
        )

        setup = strategy.generate_setup(bars, 20)

        self.assertIsNotNone(setup)
        self.assertEqual(setup.direction, "short")
        self.assertEqual(setup.entry_type, "market")
        self.assertEqual(setup.entry, 89.0)
        self.assertGreater(setup.stop_loss, setup.entry)

    def test_current_candle_is_excluded_from_channel(self):
        bars = make_bars(25)

        bars[20] = Bar(
            time=bars[20].time,
            open=105.0,
            high=200.0,
            low=104.0,
            close=105.0,
        )

        strategy = DonchianATRStrategy(
            channel_period=20,
            atr_period=14,
            atr_multiplier=2.0,
        )

        setup = strategy.generate_setup(bars, 20)

        self.assertIsNone(setup)


if __name__ == "__main__":
    unittest.main()
