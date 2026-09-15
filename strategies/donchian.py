from engine.data import Bar
from engine.setup import TradeSetup
from research.indicators import (
    atr,
    highest_high,
    lowest_low,
)
from strategies.base import Strategy


class DonchianATRStrategy(Strategy):
    """
    Donchian breakout with ATR-based protective stop.

    Signal:
        Long  = close breaks previous channel high.
        Short = close breaks previous channel low.

    Execution:
        Market order at next bar open.

    Exit:
        Protective ATR stop.

    The strategy itself does not use the current candle when
    constructing the breakout channel.
    """

    def __init__(
        self,
        channel_period: int = 20,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
    ):
        if channel_period <= 0:
            raise ValueError(
                "channel_period must be positive"
            )

        if atr_period <= 0:
            raise ValueError(
                "atr_period must be positive"
            )

        if atr_multiplier <= 0:
            raise ValueError(
                "atr_multiplier must be positive"
            )

        self.channel_period = channel_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier

    def generate_setup(
        self,
        bars: list[Bar],
        index: int,
    ) -> TradeSetup | None:

        minimum_history = max(
            self.channel_period,
            self.atr_period,
        )

        if index < minimum_history:
            return None

        channel_start = index - self.channel_period
        channel_end = index

        upper_channel = highest_high(
            bars,
            channel_start,
            channel_end,
        )

        lower_channel = lowest_low(
            bars,
            channel_start,
            channel_end,
        )

        current_bar = bars[index]

        current_atr = atr(
            bars,
            index,
            self.atr_period,
        )

        if current_atr is None:
            return None

        if current_bar.close > upper_channel:
            entry = current_bar.close

            stop = (
                entry
                - current_atr * self.atr_multiplier
            )

            return TradeSetup(
                direction="long",
                entry=entry,
                stop_loss=stop,
                take_profit=None,
                reason=(
                    f"donchian_long_"
                    f"{self.channel_period}"
                ),
                entry_type="market",
            )

        if current_bar.close < lower_channel:
            entry = current_bar.close

            stop = (
                entry
                + current_atr * self.atr_multiplier
            )

            return TradeSetup(
                direction="short",
                entry=entry,
                stop_loss=stop,
                take_profit=None,
                reason=(
                    f"donchian_short_"
                    f"{self.channel_period}"
                ),
                entry_type="market",
            )

        return None
