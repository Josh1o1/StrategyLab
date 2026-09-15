from dataclasses import dataclass

from .data import Bar
from .positions import Position


@dataclass(frozen=True)
class ExitResult:
    price: float
    reason: str


class ExecutionSimulator:
    """
    Conservative OHLC execution model.

    Rules:
    - Signals are generated on a completed candle.
    - Entries occur on the next candle's open.
    - Gaps beyond SL/TP fill at the actual open.
    - If both SL and TP are touched inside one candle,
      assume the stop was hit first.
    """

    @staticmethod
    def entry_price(bar: Bar) -> float:
        return bar.open

    @staticmethod
    def check_exit(
        position: Position,
        bar: Bar,
    ) -> ExitResult | None:

        if position.direction == "long":
            stop_hit = bar.low <= position.stop_loss

            target_hit = (
                position.take_profit is not None
                and bar.high >= position.take_profit
            )

            # Gap through stop.
            if bar.open <= position.stop_loss:
                return ExitResult(bar.open, "stop_gap")

            # Gap through target.
            if (
                position.take_profit is not None
                and bar.open >= position.take_profit
            ):
                return ExitResult(bar.open, "take_profit_gap")

            # Conservative ambiguity rule: SL first.
            if stop_hit:
                return ExitResult(position.stop_loss, "stop")

            if target_hit:
                return ExitResult(position.take_profit, "take_profit")

        elif position.direction == "short":
            stop_hit = bar.high >= position.stop_loss

            target_hit = (
                position.take_profit is not None
                and bar.low <= position.take_profit
            )

            # Gap through stop.
            if bar.open >= position.stop_loss:
                return ExitResult(bar.open, "stop_gap")

            # Gap through target.
            if (
                position.take_profit is not None
                and bar.open <= position.take_profit
            ):
                return ExitResult(bar.open, "take_profit_gap")

            # Conservative ambiguity rule: SL first.
            if stop_hit:
                return ExitResult(position.stop_loss, "stop")

            if target_hit:
                return ExitResult(position.take_profit, "take_profit")

        else:
            raise ValueError("Invalid position direction")

        return None
