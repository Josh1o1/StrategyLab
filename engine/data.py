from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self):
        if self.open <= 0 or self.high <= 0 or self.low <= 0 or self.close <= 0:
            raise ValueError("OHLC prices must be positive")

        if self.high < max(self.open, self.close):
            raise ValueError("High cannot be below open or close")

        if self.low > min(self.open, self.close):
            raise ValueError("Low cannot be above open or close")


@dataclass(frozen=True)
class Signal:
    direction: str
    reason: str = ""

    def __post_init__(self):
        if self.direction not in {"long", "short", "flat"}:
            raise ValueError("direction must be long, short, or flat")
