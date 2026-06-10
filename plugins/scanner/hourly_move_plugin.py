from database import (
    hourly_alert_exists,
    save_hourly_alert
)
from plugins.base_hourly_plugin import (
    BaseHourlyPlugin
)

class HourlyMovePlugin(
    BaseHourlyPlugin
):

    THRESHOLD = 10

    def process(
        self,
        symbol,
        candles
    ):

        candle = candles[-2]

        events = []

        candle_time = candle["close_time"]

        if hourly_alert_exists(
            symbol,
            candle_time
        ):
            return events

        open_price = float(
            candle["open"]
        )

        close_price = float(
            candle["close"]
        )

        move_pct = (
            (close_price - open_price)
            / open_price
        ) * 100

        if abs(move_pct) < self.THRESHOLD:
            return events

        save_hourly_alert(
            symbol,
            candle_time
        )

        direction = (
            "UP"
            if move_pct > 0
            else "DOWN"
        )

        notes = (
            f"{symbol} moved "
            f"{move_pct:.2f}% "
            f"in the last completed 1h candle.\n\n"
            f"Direction: {direction}\n"
            f"Open: {open_price}\n"
            f"Close: {close_price}"
        )

        events.append(
            {
                "symbol": symbol,
                "price": close_price,
                "notes": notes,
                "type": "hourly_move"
            }
        )

        return events