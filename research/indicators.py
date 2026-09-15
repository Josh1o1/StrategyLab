from engine.data import Bar


def true_range(
    bars: list[Bar],
    index: int,
) -> float:
    """
    True Range for one completed bar.
    """

    bar = bars[index]

    if index == 0:
        return bar.high - bar.low

    previous_close = bars[index - 1].close

    return max(
        bar.high - bar.low,
        abs(bar.high - previous_close),
        abs(bar.low - previous_close),
    )


def atr(
    bars: list[Bar],
    index: int,
    period: int,
) -> float | None:
    """
    Simple Average True Range.

    Uses only completed bars through `index`.
    Returns None until enough history exists.
    """

    if period <= 0:
        raise ValueError("period must be positive")

    if index < period - 1:
        return None

    values = [
        true_range(bars, i)
        for i in range(
            index - period + 1,
            index + 1,
        )
    ]

    return sum(values) / period


def highest_high(
    bars: list[Bar],
    start: int,
    end: int,
) -> float:
    """
    Highest high in bars[start:end].

    `end` is exclusive.
    """

    if start < 0 or end > len(bars):
        raise IndexError("channel range out of bounds")

    if start >= end:
        raise ValueError("channel range must not be empty")

    return max(
        bar.high
        for bar in bars[start:end]
    )


def lowest_low(
    bars: list[Bar],
    start: int,
    end: int,
) -> float:
    """
    Lowest low in bars[start:end].

    `end` is exclusive.
    """

    if start < 0 or end > len(bars):
        raise IndexError("channel range out of bounds")

    if start >= end:
        raise ValueError("channel range must not be empty")

    return min(
        bar.low
        for bar in bars[start:end]
    )
