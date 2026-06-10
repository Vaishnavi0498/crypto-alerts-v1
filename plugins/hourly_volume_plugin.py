from plugins.base_hourly_plugin import (
    BaseHourlyPlugin
)

class HourlyVolumePlugin(
    BaseHourlyPlugin
):

    MULTIPLIER = 3

    def process(
        self,
        symbol,
        candles
    ):

        events = []

        latest = candles[-2]

        previous = candles[:-2]

        avg_volume = (
            sum(
                c["volume"]
                for c in previous
            )
            /
            len(previous)
        )

        if (
            latest["volume"]
            <
            avg_volume * self.MULTIPLIER
        ):
            return events

        notes = (
            f"Volume Spike\n\n"
            f"Current Volume: "
            f"{latest['volume']:.2f}\n"
            f"Average Volume: "
            f"{avg_volume:.2f}"
        )

        events.append(
            {
                "symbol": symbol,
                "price": latest["close"],
                "notes": notes,
                "type": "volume_spike"
            }
        )

        return events