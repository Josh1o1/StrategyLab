from dataclasses import dataclass, field

from .costs import CostModel
from .data import Bar
from .execution import ExecutionSimulator
from .positions import Position
from .setup import TradeSetup


@dataclass
class Trade:
    direction: str
    entry_time: object
    entry_price: float
    exit_time: object
    exit_price: float
    size: float
    pnl: float
    exit_reason: str
    strategy_reason: str = ""
    initial_risk: float = 0.0
    entry_cost: float = 0.0
    exit_cost: float = 0.0
    gross_pnl: float = 0.0

    @property
    def r_multiple(self) -> float:
        if self.initial_risk <= 0:
            return 0.0

        return self.pnl / self.initial_risk


@dataclass(frozen=True)
class EquityPoint:
    time: object
    equity: float
    trade_pnl: float
    cumulative_pnl: float


@dataclass
class BacktestResult:
    starting_equity: float
    ending_equity: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)

    @property
    def net_pnl(self) -> float:
        return self.ending_equity - self.starting_equity

    @property
    def return_pct(self) -> float:
        if self.starting_equity == 0:
            return 0.0

        return (
            self.net_pnl
            / self.starting_equity
            * 100.0
        )


class BacktestEngine:
    """
    Core historical execution engine.

    Execution rules:

    Completed bar
        ↓
    strategy creates setup
        ↓
    market → next bar open
    limit/stop → pending order

    Pending limit/stop orders have an optional max_bars lifetime.
    """

    def __init__(
        self,
        starting_equity: float = 10_000.0,
        risk_fraction: float = 0.01,
        costs: CostModel | None = None,
    ):
        if starting_equity <= 0:
            raise ValueError(
                "starting_equity must be positive"
            )

        if risk_fraction <= 0:
            raise ValueError(
                "risk_fraction must be positive"
            )

        self.starting_equity = starting_equity
        self.equity = starting_equity
        self.risk_fraction = risk_fraction
        self.costs = costs or CostModel()
        self.execution = ExecutionSimulator()

    def position_size(
        self,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        distance = abs(
            entry_price - stop_loss
        )

        if distance <= 0:
            raise ValueError(
                "Stop distance must be positive"
            )

        risk_amount = (
            self.equity * self.risk_fraction
        )

        return risk_amount / distance

    def _open_position(
        self,
        setup: TradeSetup,
        bar: Bar,
    ) -> Position:
        if setup.entry_type == "market":
            entry_price = bar.open
        else:
            entry_price = setup.entry

        size = self.position_size(
            entry_price,
            setup.stop_loss,
        )

        entry_cost = self.costs.entry_cost(size)

        self.equity -= entry_cost

        return Position(
            direction=setup.direction,
            entry_time=bar.time,
            entry_price=entry_price,
            size=size,
            stop_loss=setup.stop_loss,
            take_profit=setup.take_profit,
        )

    def _close_position(
        self,
        position: Position,
        bar: Bar,
        exit_price: float,
        exit_reason: str,
        strategy_reason: str,
    ) -> Trade:

        entry_cost = self.costs.entry_cost(
            position.size
        )
        exit_cost = self.costs.exit_cost(
            position.size
        )

        if position.direction == "long":
            gross_pnl = (
                exit_price - position.entry_price
            ) * position.size

        elif position.direction == "short":
            gross_pnl = (
                position.entry_price - exit_price
            ) * position.size

        else:
            raise ValueError(
                "Invalid position direction"
            )

        net_pnl = (
            gross_pnl
            - entry_cost
            - exit_cost
        )

        # Entry cost was already deducted from equity when
        # the position opened. Therefore only the trade's
        # gross result minus exit cost is added here.
        self.equity += gross_pnl - exit_cost

        initial_risk = (
            abs(position.entry_price - position.stop_loss)
            * position.size
        )

        return Trade(
            direction=position.direction,
            entry_time=position.entry_time,
            entry_price=position.entry_price,
            exit_time=bar.time,
            exit_price=exit_price,
            size=position.size,
            pnl=net_pnl,
            exit_reason=exit_reason,
            strategy_reason=strategy_reason,
            initial_risk=initial_risk,
            entry_cost=entry_cost,
            exit_cost=exit_cost,
            gross_pnl=gross_pnl,
        )

    @staticmethod
    def _entry_triggered(
        setup: TradeSetup,
        bar: Bar,
    ) -> bool:

        if setup.entry_type == "market":
            return True

        if setup.direction == "long":
            if setup.entry_type == "limit":
                return bar.low <= setup.entry

            if setup.entry_type == "stop":
                return bar.high >= setup.entry

        if setup.direction == "short":
            if setup.entry_type == "limit":
                return bar.high >= setup.entry

            if setup.entry_type == "stop":
                return bar.low <= setup.entry

        return False

    @staticmethod
    def _pending_order_expired(
        setup: TradeSetup,
        age: int,
    ) -> bool:

        if setup.max_bars is None:
            return False

        return age > setup.max_bars

    def run_strategy(
        self,
        strategy,
        bars: list[Bar],
    ) -> BacktestResult:
        if len(bars) < 2:
            return BacktestResult(
                starting_equity=self.starting_equity,
                ending_equity=self.equity,
            )

        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []

        position: Position | None = None
        active_reason = ""

        pending_setup: TradeSetup | None = None
        pending_reason = ""
        pending_age = 0

        scheduled_market_setup: TradeSetup | None = None
        scheduled_market_reason = ""

        for index in range(len(bars)):
            bar = bars[index]
            bar_trade_pnl = 0.0

            # 1. Execute a market setup scheduled by the previous bar.
            if (
                position is None
                and scheduled_market_setup is not None
            ):
                position = self._open_position(
                    scheduled_market_setup,
                    bar,
                )
                active_reason = scheduled_market_reason

                scheduled_market_setup = None
                scheduled_market_reason = ""

                # A market entry can hit its stop/target on the
                # same bar.
                exit_result = self.execution.check_exit(
                    position,
                    bar,
                )

                if exit_result is not None:
                    trade = self._close_position(
                        position=position,
                        bar=bar,
                        exit_price=exit_result.price,
                        exit_reason=exit_result.reason,
                        strategy_reason=active_reason,
                    )
                    trades.append(trade)
                    bar_trade_pnl += trade.pnl
                    position = None
                    active_reason = ""

            # 2. Manage an already-open position.
            if position is not None:
                exit_result = self.execution.check_exit(
                    position,
                    bar,
                )

                if exit_result is not None:
                    trade = self._close_position(
                        position=position,
                        bar=bar,
                        exit_price=exit_result.price,
                        exit_reason=exit_result.reason,
                        strategy_reason=active_reason,
                    )
                    trades.append(trade)
                    bar_trade_pnl += trade.pnl
                    position = None
                    active_reason = ""

            # 3. Check pending limit/stop orders.
            if (
                position is None
                and pending_setup is not None
            ):
                pending_age += 1

                if self._pending_order_expired(
                    pending_setup,
                    pending_age,
                ):
                    pending_setup = None
                    pending_reason = ""
                    pending_age = 0

                elif self._entry_triggered(
                    pending_setup,
                    bar,
                ):
                    position = self._open_position(
                        pending_setup,
                        bar,
                    )
                    active_reason = pending_reason

                    pending_setup = None
                    pending_reason = ""
                    pending_age = 0

                    # A pending order can enter and exit on the
                    # same bar.
                    exit_result = self.execution.check_exit(
                        position,
                        bar,
                    )

                    if exit_result is not None:
                        trade = self._close_position(
                            position=position,
                            bar=bar,
                            exit_price=exit_result.price,
                            exit_reason=exit_result.reason,
                            strategy_reason=active_reason,
                        )
                        trades.append(trade)
                        bar_trade_pnl += trade.pnl
                        position = None
                        active_reason = ""

            # 4. Generate a new strategy setup.
            if (
                position is None
                and pending_setup is None
                and scheduled_market_setup is None
            ):
                setup = strategy.generate_setup(
                    bars,
                    index,
                )

                if setup is not None:
                    if setup.entry_type == "market":
                        # Market signals execute at the next bar's open.
                        if index + 1 < len(bars):
                            scheduled_market_setup = setup
                            scheduled_market_reason = setup.reason
                    else:
                        pending_setup = setup
                        pending_reason = setup.reason
                        pending_age = 0

            # 5. Exactly one realized-equity observation per bar.
            equity_curve.append(
                EquityPoint(
                    time=bar.time,
                    equity=self.equity,
                    trade_pnl=bar_trade_pnl,
                    cumulative_pnl=(
                        self.equity - self.starting_equity
                    ),
                )
            )

        return BacktestResult(
            starting_equity=self.starting_equity,
            ending_equity=self.equity,
            trades=trades,
            equity_curve=equity_curve,
        )

