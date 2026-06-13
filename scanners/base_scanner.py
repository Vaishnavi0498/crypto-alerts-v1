import time

from notifications import send_alert

from symbol_service import get_symbols

from data_sources.binance_klines import (
    get_recent_candles
)


class BaseScanner:

    INTERVAL = "1h"

    LIMIT = 100

    SLEEP_SECONDS = 300

    def __init__(
        self,
        plugins
    ):

        self.plugins = plugins

        self.symbols = (
            get_symbols()
        )

        print(
            f"Loaded {len(self.symbols)} symbols"
        )

    def scan_symbol(
        self,
        symbol
    ):

        candles = get_recent_candles(
            symbol=symbol,
            interval=self.INTERVAL,
            limit=self.LIMIT
        )

        for plugin in self.plugins:

            events = plugin.process(
                symbol,
                candles
            )

            for event in events:

                send_alert(
                    symbol=event["symbol"],
                    price=event["price"],
                    notes=event["notes"]
                )

    def run(self):

        while True:

            print(
                f"Starting {self.INTERVAL} scan..."
            )

            for symbol in self.symbols:

                try:

                    self.scan_symbol(
                        symbol
                    )

                except Exception as e:

                    print(
                        f"SCAN ERROR {symbol}: {e}"
                    )

            print(
                "Scan complete."
            )

            time.sleep(
                self.SLEEP_SECONDS
            )