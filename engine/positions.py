from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    direction: str
    entry_time: datetime
    entry_price: float
    size: float
    stop_loss: float
    take_profit: float | None = None

    exit_time: datetime | None = None
    exit_price: float | None = None
    exit_reason: str | None = None

    @property
    def is_open(self) -> bool:
        return self.exit_time is None

    @property
    def risk_per_unit(self) -> float:
        return abs(self.entry_price - self.stop_loss)

    @property
    def pnl(self) -> float | None:
        if self.exit_price is None:
            return None

        if self.direction == "long":
            return (self.exit_price - self.entry_price) * self.size

        if self.direction == "short":
            return (self.entry_price - self.exit_price) * self.size

        raise ValueError("Invalid position direction")
