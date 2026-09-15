from engine.data import Bar
from engine.setup import TradeSetup

from .base import Strategy


class TestLongStrategy(Strategy):
    name = "test_long"

    def generate_setup(
        self,
        bars: list[Bar],
        index: int,
    ) -> TradeSetup | None:

        if index != 0:
            return None

        bar = bars[index]

        return TradeSetup(
            direction="long",
            entry=bar.close,
            stop_loss=bar.close - 2.0,
            take_profit=bar.close + 4.0,
            reason="laboratory test setup",
            entry_type="market",
        )
