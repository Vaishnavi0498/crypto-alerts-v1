import threading
from datetime import datetime, timezone

from data_sources.binance_daily_klines import (
    get_daily_candles,
)


class RollingHighService:

    LOOKBACK_DAYS = 30

    def __init__(self):

        self.lock = threading.Lock()

        self.monthly_highs = {}

        self.last_alerted_level = {}

        self.last_refresh_date = None

    def _today(self):

        return datetime.now(
            timezone.utc
        ).date()

    def refresh_if_required(
        self,
        symbols
    ):

        today = self._today()

        with self.lock:

            if self.last_refresh_date == today:

                return

            print(
                "Refreshing 30-day highs..."
            )

            for symbol in symbols:

                try:

                    candles = get_daily_candles(
                        symbol=symbol,
                        limit=self.LOOKBACK_DAYS + 1
                    )

                    if len(candles) < 2:

                        continue

                    completed_days = candles[:-1]

                    monthly_high = max(
                        candle["high"]
                        for candle in completed_days
                    )

                    self.monthly_highs[
                        symbol
                    ] = monthly_high

                except Exception as e:

                    print(
                        f"{symbol}: {e}"
                    )

            self.last_refresh_date = today

            print(
                "30-day high refresh complete."
            )

    def get_high(
        self,
        symbol
    ):

        with self.lock:

            return self.monthly_highs.get(
                symbol
            )


    def get_last_alerted_level(
        self,
        symbol
    ):

        with self.lock:

            return self.last_alerted_level.get(
                symbol
            )


    def mark_alerted(
        self,
        symbol,
        level
    ):

        with self.lock:

            self.last_alerted_level[
                symbol
            ] = level

    def refresh(
        self,
        symbols
    ):

        with self.lock:

            self.last_refresh_date = None

        self.refresh_if_required(
            symbols
        )


rolling_high_service = (
    RollingHighService()
)