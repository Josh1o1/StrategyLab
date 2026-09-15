from abc import ABC, abstractmethod

from engine.data import Bar
from engine.setup import TradeSetup


class Strategy(ABC):
    """
    Base contract for every StrategyLab strategy.

    A strategy receives completed historical bars and may
    produce a trade setup using information available up
    to that point only.
    """

    name = "unnamed"

    @abstractmethod
    def generate_setup(
        self,
        bars: list[Bar],
        index: int,
    ) -> TradeSetup | None:
        """
        Generate a setup using bars[:index + 1].

        The current bar is assumed to be CLOSED.
        The engine is responsible for execution.
        """
        raise NotImplementedError
