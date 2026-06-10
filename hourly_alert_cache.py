triggered_candles = set()


def already_alerted(symbol, candle_time):

    return (
        symbol,
        candle_time
    ) in triggered_candles


def mark_alerted(symbol, candle_time):

    triggered_candles.add(
        (
            symbol,
            candle_time
        )
    )