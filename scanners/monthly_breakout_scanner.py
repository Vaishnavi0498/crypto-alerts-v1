import math
import time
import threading

from concurrent.futures import (
    ThreadPoolExecutor,
)

from batcher import (
    background_flush_loop,
)

from scanners.base_scanner import (
    BaseScanner,
)

from plugins.scanner.plugin_manager import (
    load_plugins,
)

from services.rolling_high_service import (
    rolling_high_service,
)


class MonthlyBreakoutScanner(
    BaseScanner
):

    INTERVAL = "1m"

    LIMIT = 2

    MAX_WORKERS = 20

    def __init__(self):

        super().__init__(
            plugins=load_plugins(
                "monthly"
            )
        )
        
        rolling_high_service.refresh(
            self.symbols
        )

    def run(self):

        threading.Thread(
            target=background_flush_loop,
            daemon=True,
        ).start()

        while True:

            rolling_high_service.refresh_if_required(
                self.symbols
            )

            print(
                "Starting Monthly Breakout Scan..."
            )

            with ThreadPoolExecutor(
                max_workers=self.MAX_WORKERS
            ) as executor:

                executor.map(
                    self._safe_scan_symbol,
                    self.symbols,
                )

            print(
                "Monthly Breakout Scan Complete."
            )

            now = time.time()

            next_close = (
                math.floor(now / 60) + 1
            ) * 60

            sleep_time = max(
                1,
                next_close - now + 2,
            )

            print(
                f"Sleeping {sleep_time:.1f}s until next 1m candle..."
            )

            time.sleep(
                sleep_time
            )


if __name__ == "__main__":

    MonthlyBreakoutScanner().run()