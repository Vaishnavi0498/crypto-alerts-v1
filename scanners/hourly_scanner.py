import time
from scanners.base_scanner import (
    BaseScanner
)

from symbol_loader import (
    get_all_futures_symbols
)

from notifications import (
    send_alert
)

from plugins.hourly_plugin_manager import (
    load_hourly_plugins
)

from data_sources.binance_klines import (
    get_recent_candles
)

CHECK_INTERVAL_SECONDS = 300


class HourlyScanner(
    BaseScanner
):

    def __init__(self):

        self.symbols = (
            get_all_futures_symbols()
        )

        self.plugins = (
            load_hourly_plugins()
        )

        print(
            f"Loaded {len(self.symbols)} futures symbols"
        )


    def scan_symbol(
        self,
        symbol
    ):

        try:

            candles = get_recent_candles(
                symbol,
                interval="1h",
                limit=20
            )

            if len(candles) < 20:
                return

            for plugin in self.plugins:

                events = plugin.process(
                    symbol,
                    candles
                )

                if not events:
                    continue

                for event in events:

                    send_alert(
                        symbol=event["symbol"],
                        price=event["price"],
                        notes=event["notes"]
                    )

        except Exception as e:

            print(
                f"SCAN ERROR {symbol}: {e}"
            )

    def run(self):

        while True:

            print(
                "Starting hourly scan..."
            )

            for symbol in self.symbols:

                self.scan_symbol(
                    symbol
                )

            print(
                "Scan complete."
            )

            time.sleep(
                CHECK_INTERVAL_SECONDS
            )


if __name__ == "__main__":

    scanner = HourlyScanner()

    scanner.run()