from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    spread: float = 0.0
    slippage: float = 0.0
    commission_per_unit: float = 0.0

    def entry_cost(self, size: float) -> float:
        return (
            self.spread * size
            + self.slippage * size
            + self.commission_per_unit * size
        )

    def exit_cost(self, size: float) -> float:
        return (
            self.spread * size
            + self.slippage * size
            + self.commission_per_unit * size
        )

    def round_trip_cost(self, size: float) -> float:
        return self.entry_cost(size) + self.exit_cost(size)
