import unittest

from engine.setup import TradeSetup


class TestTradeSetup(unittest.TestCase):

    def test_valid_long_setup(self):
        setup = TradeSetup(
            direction="long",
            entry=100,
            stop_loss=95,
            take_profit=110,
            reason="breakout",
        )

        self.assertEqual(setup.direction, "long")
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


if __name__ == "__main__":
    unittest.main()
