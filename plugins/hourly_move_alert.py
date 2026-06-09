from datetime import datetime, UTC


class HourlyMoveAlertPlugin:

    def __init__(self):

        self.last_alerted_candle = {}

    def process(
        self,
        symbol,
        price,
        trade=None
    ):

        return []

    def process_kline(
        self,
        symbol,
        kline
    ):

        events = []

        candle_closed = kline["x"]

        if not candle_closed:
            return events

        candle_time = kline["T"]

        cache_key = (
            symbol,
            candle_time
        )

        if cache_key in self.last_alerted_candle:
            return events

        open_price = float(
            kline["o"]
        )

        close_price = float(
            kline["c"]
        )

        move_pct = (
            (close_price - open_price)
            / open_price
        ) * 100

        if abs(move_pct) < 10:
            return events

        self.last_alerted_candle[
            cache_key
        ] = True

        direction = (
            "UP"
            if move_pct > 0
            else "DOWN"
        )

        notes = (
            f"{symbol} moved "
            f"{move_pct:.2f}% "
            f"in the last hourly candle.\n\n"
            f"Direction: {direction}\n"
            f"Open: {open_price}\n"
            f"Close: {close_price}"
        )

        events.append(
            {
                "alert_id": None,
                "symbol": symbol,
                "price": close_price,
                "notes": notes,
                "type": "hourly_move"
            }
        )

        return events