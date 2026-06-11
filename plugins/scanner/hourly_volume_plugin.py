from plugins.scanner.base_plugin import (
    BasePlugin
)


class HourlyVolumePlugin(
    BasePlugin
):

    ALERT_TYPE = "VOLUME"

    MULTIPLIER = 20

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

        notes = (
            f"Volume Spike\n\n"
            f"Current Volume: "
            f"{latest['volume']:.2f}\n"
            f"Average Volume: "
            f"{avg_volume:.2f}"
        )

        return [
            {
                "symbol": symbol,
                "price": latest["close"],
                "notes": notes,
                "type": "volume_spike"
            }
        ]