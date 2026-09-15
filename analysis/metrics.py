from dataclasses import dataclass

from engine.backtest import Trade


@dataclass(frozen=True)
class PerformanceMetrics:
    starting_equity: float
    ending_equity: float
    net_pnl: float
    return_pct: float

    trade_count: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int

    win_rate_pct: float
    average_trade: float
    average_win: float
    average_loss: float

    gross_profit: float
    gross_loss: float
    profit_factor: float

    expectancy: float

    max_drawdown: float
    max_drawdown_pct: float


def calculate_metrics(
    starting_equity: float,
    trades: list[Trade],
) -> PerformanceMetrics:
    if starting_equity <= 0:
        raise ValueError(
            "starting_equity must be positive"
        )

    equity = starting_equity
    peak_equity = starting_equity

    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    winning = []
    losing = []
    breakeven = []

    for trade in trades:
        equity += trade.pnl

        if trade.pnl > 0:
            winning.append(trade.pnl)
        elif trade.pnl < 0:
            losing.append(trade.pnl)
        else:
            breakeven.append(trade.pnl)

        if equity > peak_equity:
            peak_equity = equity

        drawdown = peak_equity - equity

        if drawdown > max_drawdown:
            max_drawdown = drawdown

        if peak_equity > 0:
            drawdown_pct = (
                drawdown
                / peak_equity
                * 100.0
            )

            if drawdown_pct > max_drawdown_pct:
                max_drawdown_pct = drawdown_pct

    trade_count = len(trades)

    net_pnl = equity - starting_equity

    if starting_equity > 0:
        return_pct = (
            net_pnl
            / starting_equity
            * 100.0
        )
    else:
        return_pct = 0.0

    winning_count = len(winning)
    losing_count = len(losing)
    breakeven_count = len(breakeven)

    if trade_count:
        win_rate_pct = (
            winning_count
            / trade_count
            * 100.0
        )

        average_trade = (
            net_pnl
            / trade_count
        )
    else:
        win_rate_pct = 0.0
        average_trade = 0.0

    if winning:
        average_win = (
            sum(winning)
            / len(winning)
        )
    else:
        average_win = 0.0

    if losing:
        average_loss = (
            sum(losing)
            / len(losing)
        )
    else:
        average_loss = 0.0

    gross_profit = sum(winning)
    gross_loss = abs(sum(losing))

    if gross_loss > 0:
        profit_factor = (
            gross_profit
            / gross_loss
        )
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    expectancy = average_trade

    return PerformanceMetrics(
        starting_equity=starting_equity,
        ending_equity=equity,
        net_pnl=net_pnl,
        return_pct=return_pct,
        trade_count=trade_count,
        winning_trades=winning_count,
        losing_trades=losing_count,
        breakeven_trades=breakeven_count,
        win_rate_pct=win_rate_pct,
        average_trade=average_trade,
        average_win=average_win,
        average_loss=average_loss,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        expectancy=expectancy,
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_drawdown_pct,
    )
