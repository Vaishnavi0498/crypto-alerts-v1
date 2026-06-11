from database import (
    hourly_alert_exists,
    save_hourly_alert
)

from plugins.scanner.base_plugin import (
    BasePlugin
)


class RSIPlugin(BasePlugin):

    RSI_THRESHOLD = 85

    RSI_PERIOD = 14

    def calculate_rsi(
        self,
        closes
    ):

        gains = []
        losses = []

        for i in range(
            1,
            len(closes)
        ):

            diff = (
                closes[i]
                - closes[i - 1]
            )

            if diff > 0:

                gains.append(diff)
                losses.append(0)

            else:

                gains.append(0)
                losses.append(abs(diff))

        avg_gain = (
            sum(gains[-self.RSI_PERIOD:])
            / self.RSI_PERIOD
        )

        avg_loss = (
            sum(losses[-self.RSI_PERIOD:])
            / self.RSI_PERIOD
        )

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss

        rsi = (
            100
            - (
                100
                / (1 + rs)
            )
        )

        return rsi

    def process(
        self,
        symbol,
        candles
    ):

        if len(candles) < 20:
            return []

        closes = [
            float(c[4])
            for c in candles[:-1]
        ]

        rsi = self.calculate_rsi(
            closes
        )

        last_closed = candles[-2]

        candle_time = last_closed[6]

        unique_key = (
            f"{symbol}_RSI85"
        )

        if hourly_alert_exists(
            unique_key,
            candle_time
        ):
            return []

        if rsi < self.RSI_THRESHOLD:
            return []

        save_hourly_alert(
            unique_key,
            candle_time
        )

        return [
            {
                "symbol": symbol,
                "price": float(
                    last_closed[4]
                ),
                "notes":
                    f"RSI Alert\n\n"
                    f"RSI: {rsi:.2f}\n"
                    f"Threshold: {self.RSI_THRESHOLD}"
            }
        ]