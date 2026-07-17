import threading
from datetime import datetime, timezone

from data_sources.binance_daily_klines import (
    get_daily_candles,
)


class RollingHighService:

    LOOKBACK_PERIODS = [
        30,
        60,
        90,
    ]

    MAX_LOOKBACK = max(
        LOOKBACK_PERIODS
    )

    def __init__(self):

        self.lock = threading.Lock()

        self.highs = {
            30: {},
            60: {},
            90: {},
        }

        self.last_alerted_level = {
            30: {},
            60: {},
            90: {},
        }

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
                "Refreshing rolling highs..."
            )

            for symbol in symbols:

                try:

                    candles = get_daily_candles(
                        symbol=symbol,
                        limit=self.MAX_LOOKBACK + 1
                    )

                    if len(candles) < 2:

                        continue

                    completed_days = candles[:-1]

                    for lookback in self.LOOKBACK_PERIODS:

                        if len(completed_days) < lookback:

                            continue

                        period_high = max(
                            candle["high"]
                            for candle in completed_days[-lookback:]
                        )

                        self.highs[
                            lookback
                        ][
                            symbol
                        ] = period_high

                except Exception as e:

                    print(
                        f"{symbol}: {e}"
                    )

            self.last_refresh_date = today

            print(
                "Rolling high refresh complete."
            )

    def get_high(
        self,
        symbol,
        lookback
    ):

        with self.lock:

            return self.highs[
                lookback
            ].get(
                symbol
            )

    def get_last_alerted_level(
        self,
        symbol,
        lookback
    ):

        with self.lock:

            return self.last_alerted_level[
                lookback
            ].get(
                symbol
            )

    def mark_alerted(
        self,
        symbol,
        lookback,
        level
    ):

        with self.lock:

            self.last_alerted_level[
                lookback
            ][
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