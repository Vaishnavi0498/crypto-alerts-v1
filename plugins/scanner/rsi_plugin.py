from plugins.scanner.base_plugin import (
    BasePlugin
)
import textwrap
import time


class RSIPlugin(
    BasePlugin
):

    ALERT_TYPE = "RSI85"

    RSI_THRESHOLD = 85

    RSI_PERIOD = 14

    COOLDOWN_SECONDS = 30 * 60  # 30 minutes

    _last_alert_times = {}

    def calculate_rsi(self, closes):

        if len(closes) < self.RSI_PERIOD + 1:
            return None

        gains = []
        losses = []

        # Initial 14-period gains/losses
        for i in range(1, self.RSI_PERIOD + 1):

            diff = closes[i] - closes[i - 1]

            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        avg_gain = sum(gains) / self.RSI_PERIOD
        avg_loss = sum(losses) / self.RSI_PERIOD

        # Wilder smoothing
        for i in range(self.RSI_PERIOD + 1, len(closes)):

            diff = closes[i] - closes[i - 1]

            gain = max(diff, 0)
            loss = max(-diff, 0)

            avg_gain = (
                (avg_gain * (self.RSI_PERIOD - 1) + gain)
                / self.RSI_PERIOD
            )

            avg_loss = (
                (avg_loss * (self.RSI_PERIOD - 1) + loss)
                / self.RSI_PERIOD
            )

        if avg_loss == 0:
            if avg_gain == 0:
                return 50.0  # completely flat market
            return 100.0

        rs = avg_gain / avg_loss

        return 100 - (100 / (1 + rs))

    def process(
        self,
        symbol,
        candles
    ):

        if len(candles) < 200:
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

        if previous_rsi is None or current_rsi is None:
            return []

        latest = candles[-2]

        candle_time = latest["close_time"]

        if self.already_triggered(
            symbol,
            candle_time
        ):
            return []

        # Alert only on an upward crossing
        EPS = 1e-6

        if not (
            previous_rsi < self.RSI_THRESHOLD - EPS
            and current_rsi >= self.RSI_THRESHOLD - EPS
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