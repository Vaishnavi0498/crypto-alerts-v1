from plugins.scanner.base_plugin import (
    BasePlugin
)


class HourlyVolumePlugin(
    BasePlugin
):

    ALERT_TYPE = "VOLUME"

    MULTIPLIER = 100

    def process(
        self,
        symbol,
        candles
    ):

        latest = candles[-2]

        candle_time = latest["close_time"]

        if self.already_triggered(
            symbol,
            candle_time
        ):
            return []

        previous = candles[:-2]

        avg_volume = (
            sum(
                candle["volume"]
                for candle in previous
            )
            /
            len(previous)
        )

        if (
            latest["volume"]
            <
            avg_volume * self.MULTIPLIER
        ):
            return []

        self.mark_triggered(
            symbol,
            candle_time
        )

        notes = f"""
        📊 HOURLY VOLUME SPIKE

        Symbol:
        {symbol}

        Price:
        {latest["close"]}

        Current Volume:
        {latest["volume"]:.2f}

        Average Volume:
        {avg_volume:.2f}

        Volume Multiple:
        {latest["volume"] / avg_volume:.2f}x
        """
        return [
            {
                "symbol": symbol,
                "price": latest["close"],
                "notes": notes,
                "type": "volume_spike"
            }
        ]