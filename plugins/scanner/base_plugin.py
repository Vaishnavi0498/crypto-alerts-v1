from database import (
    hourly_alert_exists,
    save_hourly_alert
)


class BasePlugin:

    ALERT_TYPE = None

    def process(
        self,
        symbol,
        candles
    ):
        return []

    def already_triggered(
        self,
        symbol,
        candle_time
    ):

        return hourly_alert_exists(
            symbol,
            candle_time,
            self.ALERT_TYPE
        )

    def mark_triggered(
        self,
        symbol,
        candle_time
    ):

        save_hourly_alert(
            symbol,
            candle_time,
            self.ALERT_TYPE
        )