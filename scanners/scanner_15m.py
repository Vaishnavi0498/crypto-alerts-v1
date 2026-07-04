import math
import time
import threading

from scanners.base_scanner import BaseScanner

from plugins.scanner.plugin_manager import (
    load_plugins,
)

from batcher import (
    background_flush_loop,
)

from concurrent.futures import ThreadPoolExecutor


class Scanner15M(BaseScanner):

    INTERVAL = "15m"

    LIMIT = 300

    MAX_WORKERS = 20

    def __init__(self):

        super().__init__(
            plugins=load_plugins("15m")
        )

    def run(self):

        threading.Thread(
            target=background_flush_loop,
            daemon=True,
        ).start()

        while True:

            print(
                "Starting 15m Smart Money Scan..."
            )

            with ThreadPoolExecutor(
                max_workers=self.MAX_WORKERS
            ) as executor:

                executor.map(
                    self._safe_scan_symbol,
                    self.symbols,
                )

            print(
                "15m Scan Complete."
            )

            now = time.time()

            next_close = (
                math.floor(now / 900) + 1
            ) * 900

            sleep_time = max(
                1,
                next_close - now + 2,
            )

            print(
                f"Sleeping {sleep_time:.1f}s until next 15m candle..."
            )

            time.sleep(
                sleep_time
            )


if __name__ == "__main__":

    Scanner15M().run()