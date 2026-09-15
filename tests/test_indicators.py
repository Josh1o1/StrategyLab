import unittest
from datetime import datetime, timedelta

from engine.data import Bar
from research.indicators import (
    true_range,
    atr,
    highest_high,
    lowest_low,
)


def make_bars():
    start = datetime(2026, 1, 1)

    return [
        Bar(start, 100, 105, 99, 103),
        Bar(start + timedelta(days=1), 103, 108, 101, 106),
        Bar(start + timedelta(days=2), 106, 110, 104, 109),
        Bar(start + timedelta(days=3), 109, 111, 107, 108),
    ]


class TestIndicators(unittest.TestCase):

    def test_true_range_first_bar(self):
        bars = make_bars()

        self.assertEqual(
            true_range(bars, 0),
            6,
        )

    def test_true_range_uses_previous_close(self):
        bars = make_bars()

        # Current high-low = 7
        # High-prev_close = 5
        # Low-prev_close = 2
        self.assertEqual(
            true_range(bars, 1),
            7,
        )

    def test_atr(self):
        bars = make_bars()

        result = atr(
            bars,
            index=2,
            period=2,
        )

        # TR bar 1 = 7
        # TR bar 2 = 6
        # ATR = 6.5
        self.assertAlmostEqual(
            result,
            6.5,
        )

    def test_atr_needs_history(self):
        bars = make_bars()

        self.assertIsNone(
            atr(
                bars,
                index=0,
                period=2,
            )
        )

    def test_highest_high(self):
        bars = make_bars()

        self.assertEqual(
            highest_high(
                bars,
                0,
                3,
            ),
            110,
        )

    def test_lowest_low(self):
        bars = make_bars()

        self.assertEqual(
            lowest_low(
                bars,
                1,
                4,
            ),
            101,
        )

    def test_empty_channel_rejected(self):
        bars = make_bars()

        with self.assertRaises(ValueError):
            highest_high(
                bars,
                2,
                2,
            )

    def test_invalid_atr_period(self):
        bars = make_bars()

        with self.assertRaises(ValueError):
            atr(
                bars,
                2,
                0,
            )


if __name__ == "__main__":
    unittest.main()
