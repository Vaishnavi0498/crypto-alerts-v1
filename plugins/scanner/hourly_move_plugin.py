from plugins.scanner.base_plugin import (
    BasePlugin
)


class HourlyMovePlugin(
    BasePlugin
):

    ALERT_TYPE = "MOVE"

    THRESHOLD = 10

    def process(
        self,
        symbol,
        candles
    ):

        candle = candles[-2]

        events = []

        candle_time = candle["close_time"]

        if self.already_triggered(
            symbol,
            candle_time
        ):
            return events

        open_price = candle["open"]

        close_price = candle["close"]

        move_pct = (
            (close_price - open_price)
            / open_price
        ) * 100

        if abs(move_pct) < self.THRESHOLD:
            return events

        self.mark_triggered(
            symbol,
            candle_time
        )

        direction = (
            "UP"
            if move_pct > 0
            else "DOWN"
        )

        notes = f"""
        📈 HOURLY MOVE ALERT

        Symbol:
        {symbol}

        Price:
        {close_price}

        Move:
        {move_pct:.2f}%

        Direction:
        {direction}

        Open:
        {open_price}

        Close:
        {close_price}
        """

        events.append(
            {
                "symbol": symbol,
                "price": close_price,
                "notes": notes,
                "type": "hourly_move"
            }
        )

        return events