from plugins.scanner.base_plugin import (
    BasePlugin
)
import time


class RSIPlugin(
    BasePlugin
):

    ALERT_TYPE = "RSI85"

    RSI_THRESHOLD = 85

    RSI_PERIOD = 14

    COOLDOWN_SECONDS = 30 * 60  # 30 minutes

    _last_alert_times = {}

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

        return (
            100
            - (
                100
                / (1 + rs)
            )
        )

    def process(
        self,
        symbol,
        candles
    ):

        if len(candles) < 30:
            return []

        # Use only completed candles
        closes = [
            candle["close"]
            for candle in candles[:-1]
        ]

        previous_rsi = self.calculate_rsi(
            closes[:-1]
        )

        current_rsi = self.calculate_rsi(
            closes
        )

        latest = candles[-2]

        candle_time = latest["close_time"]

        if self.already_triggered(
            symbol,
            candle_time
        ):
            return []

        # Alert only on an upward crossing
        if not (
            previous_rsi < self.RSI_THRESHOLD
            and current_rsi >= self.RSI_THRESHOLD
        ):
            return []

        now = time.time()

        last_alert = self._last_alert_times.get(symbol)

        if (
            last_alert is not None
            and now - last_alert < self.COOLDOWN_SECONDS
        ):
            return []

        self._last_alert_times[symbol] = now

        self.mark_triggered(
            symbol,
            candle_time
        )

        return [
            {
                "symbol": symbol,
                "price": latest["close"],
                "notes":
                    f"RSI Cross Alert\n\n"
                    f"Previous RSI: {previous_rsi:.2f}\n"
                    f"Current RSI: {current_rsi:.2f}\n"
                    f"Threshold: {self.RSI_THRESHOLD}"
            }
        ]