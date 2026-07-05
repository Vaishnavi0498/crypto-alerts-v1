import time
import traceback
from batcher import queue_alert

from symbol_service import get_symbols
from concurrent.futures import ThreadPoolExecutor

from data_sources.binance_klines import (
    get_recent_candles
)

import threading
from batcher import background_flush_loop


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

                queue_alert(
                    symbol=event["symbol"],
                    price=event["price"],
                    notes=event["notes"]
                )

    MAX_WORKERS = 20

    def _safe_scan_symbol(
        self,
        symbol
    ):

        try:

            self.scan_symbol(
                symbol
            )

        except Exception:
            print(f"\n========== {symbol} ==========")
            traceback.print_exc()

    def run(self):

        threading.Thread(
            target=background_flush_loop,
            daemon=True,
        ).start()


        while True:

            print(
                f"Starting {self.INTERVAL} scan..."
            )

            with ThreadPoolExecutor(
                max_workers=self.MAX_WORKERS
            ) as executor:

                executor.map(
                    self._safe_scan_symbol,
                    self.symbols
                )

            print(
                "Scan complete."
            )

            time.sleep(
                self.SLEEP_SECONDS
            )