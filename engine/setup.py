from dataclasses import dataclass


@dataclass(frozen=True)
class TradeSetup:
    """
    Complete trade proposal produced by a strategy.

    entry_type:
        market = execute at next bar open
        limit  = wait for price to reach entry
        stop   = wait for price to break through entry

    max_bars:
        Maximum number of bars after the signal candle that a
        pending limit/stop order may remain active.
        None means no expiry.
    """

    direction: str
    entry: float
    stop_loss: float
    take_profit: float | None = None
    reason: str = ""
    entry_type: str = "market"
    max_bars: int | None = None

    def __post_init__(self):
        if self.direction not in {"long", "short"}:
            raise ValueError("direction must be long or short")

        if self.entry_type not in {"market", "limit", "stop"}:
            raise ValueError(
                "entry_type must be market, limit, or stop"
            )

        if self.entry <= 0:
            raise ValueError("entry must be positive")

        if self.stop_loss <= 0:
            raise ValueError("stop_loss must be positive")

        if self.direction == "long" and self.stop_loss >= self.entry:
            raise ValueError("long stop must be below entry")

        if self.direction == "short" and self.stop_loss <= self.entry:
            raise ValueError("short stop must be above entry")

        if self.take_profit is not None:
            if self.take_profit <= 0:
                raise ValueError("take_profit must be positive")

            if (
                self.direction == "long"
                and self.take_profit <= self.entry
            ):
                raise ValueError(
                    "long target must be above entry"
                )

            if (
                self.direction == "short"
                and self.take_profit >= self.entry
            ):
                raise ValueError(
                    "short target must be below entry"
                )

        if self.max_bars is not None:
            if not isinstance(self.max_bars, int):
                raise ValueError("max_bars must be an integer or None")

            if self.max_bars < 1:
                raise ValueError("max_bars must be at least 1")

    @property
    def risk_distance(self) -> float:
        return abs(self.entry - self.stop_loss)

    @property
    def reward_distance(self) -> float | None:
        if self.take_profit is None:
            return None

        return abs(self.take_profit - self.entry)

    @property
    def risk_reward(self) -> float | None:
        if self.reward_distance is None:
            return None

        return self.reward_distance / self.risk_distance
